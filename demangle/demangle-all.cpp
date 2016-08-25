#include "demangle.h"
#include "swift/Basic/Demangle.h"
#include <cxxabi.h>

int _demangle_swift(
    const char *symbol, char *buffer, size_t buffer_length, int simplified)
{
    swift::Demangle::DemangleOptions options;
    if (simplified) {
        options =
            swift::Demangle::DemangleOptions::SimplifiedUIDemangleOptions();
    }

    std::string demangled =
        swift::Demangle::demangleSymbolAsString(symbol, options);

    if (demangled.size() == 0 || demangled.size() >= buffer_length) {
        return false;
    }

    memcpy(buffer, demangled.c_str(), demangled.size());
    buffer[demangled.size()] = '\0';
    return true;
}

int demangle_swift(const char *symbol, char *buffer, size_t buffer_length)
{
    return _demangle_swift(symbol, buffer, buffer_length, 0);
}

int demangle_swift_simplified(
    const char *symbol, char *buffer, size_t buffer_length)
{
    return _demangle_swift(symbol, buffer, buffer_length, 1);
}

int demangle_cpp(const char *symbol, char *buffer, size_t buffer_length)
{
    int status = 0;
    char *demangled = __cxxabiv1::__cxa_demangle(
        symbol, nullptr, nullptr, &status);

    if (status != 0 || !demangled) {
        free(demangled);
        return false;
    }

    size_t end = strlen(demangled);
    if (end >= buffer_length) {
        free(demangled);
        return false;
    }
    memcpy(buffer, demangled, end);
    buffer[end] = '\0';
    free(demangled);
    return true;
}

// also compile these things in.
#include "swift/Basic/Demangle.cpp"
#include "swift/Basic/Punycode.cpp"
