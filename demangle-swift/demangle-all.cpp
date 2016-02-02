#include "demangle-swift.h"
#include "swift/Basic/Demangle.h"

int demangle_swift(const char *symbol, char *buffer, size_t buffer_length)
{
    std::string demangled = swift::Demangle::demangleSymbolAsString(symbol);

    if (demangled.size() == 0 || demangled.size() >= buffer_length) {
        return false;
    }

    memcpy(buffer, demangled.c_str(), demangled.size());
    buffer[demangled.size()] = '\0';
    return true;
}

// also compile these things in.
#include "swift/Basic/Demangle.cpp"
#include "swift/Basic/Punycode.cpp"
