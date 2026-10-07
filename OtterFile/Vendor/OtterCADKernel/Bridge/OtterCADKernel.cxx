#include "OtterCADKernel.h"

#include <BRepBndLib.hxx>
#include <BRepMesh_IncrementalMesh.hxx>
#include <BRep_Tool.hxx>
#include <Bnd_Box.hxx>
#include <IGESControl_Reader.hxx>
#include <IGESData_IGESModel.hxx>
#include <IGESData_IGESEntity.hxx>
#include <IMeshTools_Parameters.hxx>
#include <Interface_CheckIterator.hxx>
#include <Interface_Static.hxx>
#include <Message.hxx>
#include <Message_Messenger.hxx>
#include <Message_ProgressIndicator.hxx>
#include <Message_ProgressRange.hxx>
#include <Poly_Triangulation.hxx>
#include <STEPControl_Reader.hxx>
#include <Standard_Failure.hxx>
#include <StepData_StepModel.hxx>
#include <StepRepr_ExternallyDefinedRepresentation.hxx>
#include <StepBasic_ExternalSource.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <XSControl_TransferReader.hxx>
#include <XSControl_WorkSession.hxx>
#include <gp_Pnt.hxx>

#include <algorithm>
#include <array>
#include <atomic>
#include <cerrno>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <memory>
#include <mutex>
#include <string>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <vector>

struct OtterCADMesh {
    std::vector<float> positions;
    std::vector<float> normals;
    std::vector<uint32_t> indices;
    uint64_t faces = 0;
    std::array<float, 3> minimum = {INFINITY, INFINITY, INFINITY};
    std::array<float, 3> maximum = {-INFINITY, -INFINITY, -INFINITY};
};

namespace {
std::mutex kernelMutex;
constexpr uint64_t hardFileBytes = 256 * 1024 * 1024;
// Dense STEP control-point/reference tables are not face/mesh complexity. This
// remains a bounded post-ReadFile guard, not a cap on parser peak allocations.
constexpr int hardStepEntities = 2500000;
constexpr uint64_t hardFaces = 100000;
constexpr uint64_t hardTriangles = 500000;
constexpr uint64_t hardVertices = 1500000;

bool cancelled(OtterCADCancelCallback callback, void *context) {
    return callback && callback(context) != 0;
}

OtterCADStatus fail(OtterCADStatus status, const char *message, char *error, size_t capacity) {
    if (error && capacity) {
        const size_t count = std::min(capacity - 1, std::strlen(message));
        std::memcpy(error, message, count);
        error[count] = 0;
    }
    return status;
}

class CancelProgress final : public Message_ProgressIndicator {
public:
    CancelProgress(OtterCADCancelCallback callback, void *context) : callback_(callback), context_(context) {}
    bool WasCancelled() const { return interrupted_.load(); }
protected:
    Standard_Boolean UserBreak() override {
        if (interrupted_.load()) return true;
        if (cancelled(callback_, context_)) { interrupted_.store(true); return true; }
        return false;
    }
    void Show(const Message_ProgressScope&, const Standard_Boolean) override {}
private:
    OtterCADCancelCallback callback_;
    void *context_;
    std::atomic<bool> interrupted_ {false};
};

class ScopedPrinters {
public:
    ScopedPrinters() : saved_(Message::DefaultMessenger()->Printers()) {
        Message::DefaultMessenger()->ChangePrinters().Clear();
    }
    ~ScopedPrinters() { Message::DefaultMessenger()->ChangePrinters() = saved_; }
private:
    Message_SequenceOfPrinters saved_;
};

class FileDescriptor {
public:
    explicit FileDescriptor(int value) : value_(value) {}
    ~FileDescriptor() { if (value_ >= 0) close(value_); }
    int get() const { return value_; }
private:
    int value_;
};

bool sameSnapshot(const struct stat &first, const struct stat &second) {
    return first.st_dev == second.st_dev && first.st_ino == second.st_ino
        && first.st_size == second.st_size && first.st_mtimespec.tv_sec == second.st_mtimespec.tv_sec
        && first.st_mtimespec.tv_nsec == second.st_mtimespec.tv_nsec
        && first.st_ctimespec.tv_sec == second.st_ctimespec.tv_sec
        && first.st_ctimespec.tv_nsec == second.st_ctimespec.tv_nsec;
}
}

extern "C" OtterCADStatus otter_cad_read_mesh(const char *path, const char *format,
    const OtterCADLimits *requested, OtterCADCancelCallback callback, void *context,
    OtterCADMesh **outMesh, char *error, size_t errorCapacity) {
    if (outMesh) *outMesh = nullptr;
    if (error && errorCapacity) error[0] = 0;
    if (!outMesh || !path || !format || !requested || !requested->maxFileBytes
        || !requested->maxFaces || !requested->maxVertices || !requested->maxTriangles) {
        return fail(OTTER_CAD_INVALID_INPUT, "Invalid CAD input or resource limits.", error, errorCapacity);
    }
    const size_t formatLength = strnlen(format, 5);
    if (formatLength > 4) return fail(OTTER_CAD_INVALID_INPUT, "This CAD format is not supported by this reader.", error, errorCapacity);
    try {
    std::string extension(format, formatLength);
    std::transform(extension.begin(), extension.end(), extension.begin(),
        [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    const bool isSTEP = extension == "step" || extension == "stp";
    if (!isSTEP && extension != "iges" && extension != "igs") {
        return fail(OTTER_CAD_INVALID_INPUT, "This CAD format is not supported by this reader.", error, errorCapacity);
    }
    const OtterCADLimits limits = {std::min(requested->maxFileBytes, hardFileBytes),
        std::min(requested->maxFaces, hardFaces), std::min(requested->maxVertices, hardVertices),
        std::min(requested->maxTriangles, hardTriangles)};
    FileDescriptor descriptor(open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK));
    struct stat snapshot {};
    if (descriptor.get() < 0 || fstat(descriptor.get(), &snapshot) || !S_ISREG(snapshot.st_mode)) {
        return fail(OTTER_CAD_INVALID_INPUT, "The CAD snapshot must be a readable regular file.", error, errorCapacity);
    }
    if (snapshot.st_size <= 0) {
        return fail(OTTER_CAD_PARSE_FAILED, "The CAD file is empty.", error, errorCapacity);
    }
    if (static_cast<uint64_t>(snapshot.st_size) > limits.maxFileBytes) {
        return fail(OTTER_CAD_FILE_TOO_LARGE, "The CAD file exceeds the preview input limit.", error, errorCapacity);
    }
    std::unique_lock<std::mutex> lock(kernelMutex, std::defer_lock);
    while (!lock.try_lock()) {
        if (cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    if (cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
    ScopedPrinters printers;
        Handle(CancelProgress) progress = new CancelProgress(callback, context);
        TopoDS_Shape shape;
        if (isSTEP) {
            STEPControl_Reader reader;
            Interface_Static::SetCVal("xstep.cascade.unit", "MM");
            if (reader.ReadFile(path) != IFSelect_RetDone) {
                return fail(OTTER_CAD_PARSE_FAILED, "The STEP file could not be parsed.", error, errorCapacity);
            }
            reader.SetSystemLengthUnit(1.0); // V7_9_3 expresses this value in millimetres.
            const Handle(StepData_StepModel) model = reader.StepModel();
            if (model->NbEntities() > hardStepEntities) return fail(OTTER_CAD_MESH_BUDGET, "The CAD model exceeds the entity preview limit.", error, errorCapacity);
            for (int index = 1; index <= model->NbEntities(); ++index) {
                if ((index & 1023) == 0 && cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
                const Handle(Standard_Transient) entity = model->Value(index);
                if (!entity.IsNull() && (entity->IsKind(STANDARD_TYPE(StepRepr_ExternallyDefinedRepresentation))
                    || entity->IsKind(STANDARD_TYPE(StepBasic_ExternalSource)))) {
                    return fail(OTTER_CAD_PARSE_FAILED, "External CAD references are outside this preview scope.", error, errorCapacity);
                }
            }
            if (cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
            if (!reader.WS()->ModelCheckList(false).IsEmpty(true)) return fail(OTTER_CAD_PARSE_FAILED, "The STEP file contains invalid model references or syntax.", error, errorCapacity);
            const int roots = reader.NbRootsForTransfer();
            const int transferred = reader.TransferRoots(progress->Start());
            if (transferred <= 0) {
                if (progress->WasCancelled() || cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
                return fail(OTTER_CAD_NO_GEOMETRY, "The STEP file contains no transferable geometry.", error, errorCapacity);
            }
            if (progress->WasCancelled() || cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
            if (transferred < roots || !reader.WS()->TransferReader()->LastCheckList().IsEmpty(true)) {
                return fail(OTTER_CAD_PARSE_FAILED, "The STEP model could not be transferred completely.", error, errorCapacity);
            }
            shape = reader.OneShape();
        } else {
            IGESControl_Reader reader;
            Interface_Static::SetCVal("xstep.cascade.unit", "MM");
            if (reader.ReadFile(path) != IFSelect_RetDone) {
                return fail(OTTER_CAD_PARSE_FAILED, "The IGES file could not be parsed.", error, errorCapacity);
            }
            const Handle(IGESData_IGESModel) model = reader.IGESModel();
            if (model->NbEntities() > 250000) return fail(OTTER_CAD_MESH_BUDGET, "The CAD model exceeds the entity preview limit.", error, errorCapacity);
            for (int index = 1; index <= model->NbEntities(); ++index) {
                if ((index & 1023) == 0 && cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
                if (model->Entity(index)->TypeNumber() == 416) {
                    return fail(OTTER_CAD_PARSE_FAILED, "External CAD references are outside this preview scope.", error, errorCapacity);
                }
            }
            if (cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
            if (!reader.WS()->ModelCheckList(false).IsEmpty(true)) return fail(OTTER_CAD_PARSE_FAILED, "The IGES file contains invalid model references or syntax.", error, errorCapacity);
            const int roots = reader.NbRootsForTransfer();
            const int transferred = reader.TransferRoots(progress->Start());
            if (transferred <= 0) {
                if (progress->WasCancelled() || cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
                return fail(OTTER_CAD_NO_GEOMETRY, "The IGES file contains no transferable geometry.", error, errorCapacity);
            }
            if (progress->WasCancelled() || cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
            if (transferred < roots || !reader.WS()->TransferReader()->LastCheckList().IsEmpty(true)) {
                return fail(OTTER_CAD_PARSE_FAILED, "The IGES model could not be transferred completely.", error, errorCapacity);
            }
            shape = reader.OneShape();
        }
        // The branch-local reader/model/session above are destroyed before
        // meshing; shape independently retains its transferred geometry. This
        // avoids deliberately retaining the raw entity graph with the mesh,
        // but allocator caches mean it is not an immediate RSS guarantee.
        if (progress->WasCancelled() || cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
        if (shape.IsNull()) return fail(OTTER_CAD_NO_GEOMETRY, "The CAD file contains no shape geometry.", error, errorCapacity);
        uint64_t faces = 0;
        for (TopExp_Explorer explorer(shape, TopAbs_FACE); explorer.More(); explorer.Next()) {
            if (++faces > limits.maxFaces) return fail(OTTER_CAD_MESH_BUDGET, "The CAD model exceeds the face limit.", error, errorCapacity);
            if ((faces & 1023) == 0 && cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
        }
        if (!faces) return fail(OTTER_CAD_NO_GEOMETRY, "The CAD model has no surface geometry.", error, errorCapacity);
        Bnd_Box bounds;
        BRepBndLib::Add(shape, bounds, false);
        if (bounds.IsVoid() || bounds.IsOpen()) return fail(OTTER_CAD_NO_GEOMETRY, "The CAD model has no finite geometry bounds.", error, errorCapacity);
        double x0, y0, z0, x1, y1, z1;
        bounds.Get(x0, y0, z0, x1, y1, z1);
        const double span = std::max({x1 - x0, y1 - y0, z1 - z0});
        if (!std::isfinite(span) || span <= 0) return fail(OTTER_CAD_NO_GEOMETRY, "The CAD geometry bounds are invalid.", error, errorCapacity);
        const double deflection = std::max(span * 0.005, 0.01);
        auto result = std::make_unique<OtterCADMesh>();
        result->faces = faces;
        for (TopExp_Explorer explorer(shape, TopAbs_FACE); explorer.More(); explorer.Next()) {
            if (progress->WasCancelled() || cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
            const TopoDS_Face face = TopoDS::Face(explorer.Current());
            IMeshTools_Parameters parameters;
            parameters.Deflection = deflection;
            parameters.Angle = 0.35;
            parameters.Relative = false;
            parameters.InParallel = false;
            BRepMesh_IncrementalMesh mesher(face, parameters, progress->Start());
            if (progress->WasCancelled() || cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
            TopLoc_Location location;
            const Handle(Poly_Triangulation) triangles = BRep_Tool::Triangulation(face, location);
            if (triangles.IsNull() || triangles->NbTriangles() == 0) {
                return fail(OTTER_CAD_PARSE_FAILED, "A CAD surface could not be converted to a visible mesh.", error, errorCapacity);
            }
            const uint64_t incoming = static_cast<uint64_t>(triangles->NbTriangles());
            if (incoming > limits.maxTriangles - result->indices.size() / 3
                || incoming > (limits.maxVertices - result->positions.size() / 3) / 3) {
                return fail(OTTER_CAD_MESH_BUDGET, "The CAD model exceeds the mesh preview limit.", error, errorCapacity);
            }
            const size_t previousIndices = result->indices.size();
            for (int index = 1; index <= triangles->NbTriangles(); ++index) {
                if ((index & 1023) == 0 && cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
                int a, b, c;
                triangles->Triangle(index).Get(a, b, c);
                if (face.Orientation() == TopAbs_REVERSED) std::swap(b, c);
                const gp_Trsf &transform = location.Transformation();
                const gp_Pnt pa = triangles->Node(a).Transformed(transform);
                const gp_Pnt pb = triangles->Node(b).Transformed(transform);
                const gp_Pnt pc = triangles->Node(c).Transformed(transform);
                gp_XYZ normal = (pb.XYZ() - pa.XYZ()).Crossed(pc.XYZ() - pa.XYZ());
                const double magnitude = normal.Modulus();
                if (!std::isfinite(magnitude) || magnitude < 1e-15) continue;
                normal /= magnitude;
                for (const gp_Pnt &point : {pa, pb, pc}) {
                    for (int coordinate = 0; coordinate < 3; ++coordinate) {
                        const float value = static_cast<float>(point.Coord(coordinate + 1));
                        const float component = static_cast<float>(normal.Coord(coordinate + 1));
                        if (!std::isfinite(value) || !std::isfinite(component)) return fail(OTTER_CAD_PARSE_FAILED, "The CAD mesh contains invalid coordinates.", error, errorCapacity);
                        result->positions.push_back(value);
                        result->normals.push_back(component);
                        result->minimum[coordinate] = std::min(result->minimum[coordinate], value);
                        result->maximum[coordinate] = std::max(result->maximum[coordinate], value);
                    }
                    result->indices.push_back(static_cast<uint32_t>(result->indices.size()));
                }
            }
            if (result->indices.size() == previousIndices) {
                return fail(OTTER_CAD_PARSE_FAILED, "A CAD surface produced no visible triangles.", error, errorCapacity);
            }
        }
        if (result->indices.empty()) return fail(OTTER_CAD_NO_GEOMETRY, "The CAD model produced no visible triangles.", error, errorCapacity);
        struct stat afterFD {}, afterPath {};
        if (fstat(descriptor.get(), &afterFD) || lstat(path, &afterPath)
            || !sameSnapshot(snapshot, afterFD) || !sameSnapshot(snapshot, afterPath)) {
            return fail(OTTER_CAD_INVALID_INPUT, "The CAD snapshot changed during conversion.", error, errorCapacity);
        }
        if (cancelled(callback, context)) return fail(OTTER_CAD_CANCELLED, "CAD preview cancelled.", error, errorCapacity);
        *outMesh = result.release();
        return OTTER_CAD_OK;
    } catch (const std::bad_alloc&) {
        return fail(OTTER_CAD_MESH_BUDGET, "The CAD conversion exhausted available memory.", error, errorCapacity);
    } catch (const Standard_Failure&) {
        return fail(OTTER_CAD_PARSE_FAILED, "The CAD geometry could not be converted.", error, errorCapacity);
    } catch (...) {
        return fail(OTTER_CAD_INTERNAL_ERROR, "The CAD conversion failed.", error, errorCapacity);
    }
}

extern "C" OtterCADMeshView otter_cad_mesh_view(const OtterCADMesh *mesh) {
    OtterCADMeshView view {};
    if (!mesh) return view;
    view.positions = mesh->positions.data();
    view.normals = mesh->normals.data();
    view.indices = mesh->indices.data();
    view.vertexCount = mesh->positions.size() / 3;
    view.triangleCount = mesh->indices.size() / 3;
    view.faceCount = mesh->faces;
    std::copy(mesh->minimum.begin(), mesh->minimum.end(), view.bboxMin);
    std::copy(mesh->maximum.begin(), mesh->maximum.end(), view.bboxMax);
    return view;
}

extern "C" void otter_cad_mesh_release(OtterCADMesh *mesh) { delete mesh; }
extern "C" const char *otter_cad_kernel_version(void) { return "OCCT 7.9.3 / OtterCAD geometry-only ABI 1"; }
