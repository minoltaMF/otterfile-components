cmake_minimum_required(VERSION 3.24)
project(OtterCADKernel VERSION 7.9.3 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
include(SourceClosure.cmake)
include(FrameworkMetadata.cmake)

# Match OCCT's public flattened include directory without changing upstream.
set(OTTER_OCCT_INCLUDE "${CMAKE_CURRENT_BINARY_DIR}/occt-include")
file(MAKE_DIRECTORY "${OTTER_OCCT_INCLUDE}")
file(GLOB_RECURSE _occt_headers CONFIGURE_DEPENDS
     "OCCT/src/*.h" "OCCT/src/*.hxx" "OCCT/src/*.lxx"
     "OCCT/src/*.gxx" "OCCT/src/*.pxx" "OCCT/src/*.inc")
foreach(_header IN LISTS _occt_headers)
  get_filename_component(_name "${_header}" NAME)
  if(NOT EXISTS "${OTTER_OCCT_INCLUDE}/${_name}")
    file(CREATE_LINK "${_header}" "${OTTER_OCCT_INCLUDE}/${_name}" SYMBOLIC)
  endif()
endforeach()
set(OCC_VERSION_MAJOR 7)
set(OCC_VERSION_MINOR 9)
set(OCC_VERSION_MAINTENANCE 3)
set(OCCT_VERSION_DATE "2025-12-02")
set(SET_OCC_VERSION_DEVELOPMENT "// Official release; upstream source is unchanged.")
configure_file(OCCT/adm/templates/Standard_Version.hxx.in
               "${OTTER_OCCT_INCLUDE}/Standard_Version.hxx" @ONLY)

foreach(_toolkit IN LISTS OTTER_OCCT_TOOLKITS)
  add_library(${_toolkit} STATIC ${OTTER_OCCT_${_toolkit}_SOURCES})
  target_include_directories(${_toolkit} PUBLIC "${OTTER_OCCT_INCLUDE}")
  target_compile_options(${_toolkit} PRIVATE -O1 -g0 -w)
  set_target_properties(${_toolkit} PROPERTIES CXX_VISIBILITY_PRESET hidden
      C_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN YES)
endforeach()
foreach(_toolkit IN LISTS OTTER_OCCT_TOOLKITS)
  target_link_libraries(${_toolkit} PUBLIC ${OTTER_OCCT_${_toolkit}_DEPS})
endforeach()

add_library(OtterCADKernel SHARED Bridge/OtterCADKernel.cxx Bridge/include/OtterCADKernel.h)
target_include_directories(OtterCADKernel PUBLIC Bridge/include)
target_link_libraries(OtterCADKernel PRIVATE TKDESTEP TKDEIGES TKMesh)
target_compile_options(OtterCADKernel PRIVATE -O1 -g0)
set_target_properties(OtterCADKernel PROPERTIES
    FRAMEWORK TRUE FRAMEWORK_VERSION A MACOSX_FRAMEWORK_IDENTIFIER com.otterfile.cadkernel
    MACOSX_FRAMEWORK_BUNDLE_NAME OtterCADKernel
    MACOSX_FRAMEWORK_BUNDLE_VERSION "${PROJECT_VERSION}"
    MACOSX_FRAMEWORK_SHORT_VERSION_STRING "${PROJECT_VERSION}"
    MACOSX_FRAMEWORK_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/Bridge/Info.plist.in"
    PUBLIC_HEADER "Bridge/include/OtterCADKernel.h"
    INSTALL_NAME_DIR "@rpath" BUILD_WITH_INSTALL_NAME_DIR TRUE
    XCODE_ATTRIBUTE_DEFINES_MODULE YES
    CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN YES)
if(APPLE)
  target_link_options(OtterCADKernel PRIVATE
      "-Wl,-dead_strip" "-Wl,-exported_symbols_list,${CMAKE_CURRENT_SOURCE_DIR}/Bridge/exports.txt")
  add_custom_command(TARGET OtterCADKernel POST_BUILD
      COMMAND ${CMAKE_COMMAND} "-DOTTER_CAD_FRAMEWORK=$<TARGET_BUNDLE_DIR:OtterCADKernel>"
              "-DOTTER_CAD_SOURCE=${CMAKE_CURRENT_SOURCE_DIR}" "-DOTTER_CAD_PLATFORM=${CMAKE_SYSTEM_NAME}"
              -P "${CMAKE_CURRENT_SOURCE_DIR}/Bridge/PackageFramework.cmake")
  # Packaging-only recovery for already verified binaries; no native dependency.
  add_custom_target(OtterCADKernelMetadata
      COMMAND ${CMAKE_COMMAND} "-DOTTER_CAD_FRAMEWORK=$<TARGET_BUNDLE_DIR:OtterCADKernel>"
              "-DOTTER_CAD_SOURCE=${CMAKE_CURRENT_SOURCE_DIR}" "-DOTTER_CAD_PLATFORM=${CMAKE_SYSTEM_NAME}"
              -P "${CMAKE_CURRENT_SOURCE_DIR}/Bridge/PackageFramework.cmake"
      VERBATIM)
endif()
