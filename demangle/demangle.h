/* demangle-swift.h */

#ifndef DM_DEMANGLE_H_INCLUDED
#define DM_DEMANGLE_H_INCLUDED

#ifndef DM_NOINCLUDE
#include <stdlib.h>
#include <stdbool.h>
#endif

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Demangle a Swift symbol.
 * This function will attempt to demangle the specified symbol.
 * On success, the demangled symbol is copied into buffer. If it couldn't
 * demangle (for example, if symbol was not actually a mangled symbol), it
 * does not modify buffer, and instead returns false.  The same happens if
 * the buffer is not big enough.
 *
 * @param symbol The symbol to demangle (if possible).
 * @param buffer Some memory to hold the null-terminated demangled string.
 * @param buffer_length The length of the buffer.
 * @return true if demangling was successful.
 */
int demangle_swift(const char *symbol, char *buffer, size_t buffer_length);

/**
 * Demangle a C++ symbol.
 * This function will attempt to demangle the specified symbol.
 * On success, the demangled symbol is copied into buffer. If it couldn't
 * demangle (for example, if symbol was not actually a mangled symbol), it
 * does not modify buffer, and instead returns false.  The same happens if
 * the buffer is not big enough.
 *
 * @param symbol The symbol to demangle (if possible).
 * @param buffer Some memory to hold the null-terminated demangled string.
 * @param buffer_length The length of the buffer.
 * @return true if demangling was successful.
 */
int demangle_cpp(const char *symbol, char *buffer, size_t buffer_length);

#ifdef __cplusplus
}
#endif

#endif
