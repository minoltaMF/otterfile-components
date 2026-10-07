#ifndef OTTER_CAD_KERNEL_H
#define OTTER_CAD_KERNEL_H

#include <stddef.h>
#include <stdint.h>

#if defined(__GNUC__)
#define OTTER_CAD_API __attribute__((visibility("default")))
#else
#define OTTER_CAD_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef struct OtterCADMesh OtterCADMesh;

typedef enum OtterCADStatus {
    OTTER_CAD_OK = 0,
    OTTER_CAD_INVALID_INPUT = 1,
    OTTER_CAD_FILE_TOO_LARGE = 2,
    OTTER_CAD_PARSE_FAILED = 3,
    OTTER_CAD_NO_GEOMETRY = 4,
    OTTER_CAD_MESH_BUDGET = 5,
    OTTER_CAD_CANCELLED = 6,
    OTTER_CAD_INTERNAL_ERROR = 7
} OtterCADStatus;

typedef struct OtterCADLimits {
    uint64_t maxFileBytes;
    uint64_t maxFaces;
    uint64_t maxVertices;
    uint64_t maxTriangles;
} OtterCADLimits;

/* Return nonzero to request cancellation. The callback/context must remain valid
   until read_mesh returns. Cancellation is cooperative; OCCT parsing can take
   time between checkpoints. Calls are serialized process-wide. */
typedef int (*OtterCADCancelCallback)(void *context);

typedef struct OtterCADMeshView {
    const float *positions; /* vertexCount * 3 */
    const float *normals;   /* vertexCount * 3; finite unit vectors */
    const uint32_t *indices; /* triangleCount * 3 */
    const float *colorsRGBA; /* NULL in the basic geometry-only implementation */
    uint64_t vertexCount;
    uint64_t triangleCount;
    uint64_t faceCount;
    float bboxMin[3];
    float bboxMax[3];
} OtterCADMeshView;

/* path is an app-created immutable, regular-file snapshot. format accepts only
   step/stp/iges/igs, case-insensitively. outMesh is always NULL on failure.
   Error text contains no input file contents or private pathname. No source
   files are modified; mesh coordinates use OCCT's normalized millimeter unit.
   Limits bound inputs and exported output, not OCCT intermediate allocation. */
OTTER_CAD_API OtterCADStatus otter_cad_read_mesh(const char *path,
                                 const char *format,
                                 const OtterCADLimits *limits,
                                 OtterCADCancelCallback cancel,
                                 void *context,
                                 OtterCADMesh **outMesh,
                                 char *error,
                                 size_t errorCapacity);

/* The view's arrays belong to mesh and remain valid until mesh_release. */
OTTER_CAD_API OtterCADMeshView otter_cad_mesh_view(const OtterCADMesh *mesh);
OTTER_CAD_API void otter_cad_mesh_release(OtterCADMesh *mesh);
OTTER_CAD_API const char *otter_cad_kernel_version(void);

#ifdef __cplusplus
}
#endif
#endif
