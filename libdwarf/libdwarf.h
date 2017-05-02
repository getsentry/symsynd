#ifndef LIBDWARF_H_INCLUDED
#define LIBDWARF_H_INCLUDED

typedef void dwarf_debug_info_t;

typedef struct {
    const char *message;
    int failed;
    int code;
} dwarf_error_t;

dwarf_debug_info_t *dwarf_debug_info_open_path(
    const char *path, dwarf_error_t *err_out);
void dwarf_debug_info_free(dwarf_debug_info_t *di);
const char *dwarf_debug_info_get_compilation_dir(
    dwarf_debug_info_t *di, const char *cpu_name, const char *filename,
    dwarf_error_t *err_out);
void dwarf_buffer_free(void *buf);

#endif
