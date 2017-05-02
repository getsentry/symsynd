use std::io;
use std::fmt;

use gimli;
use mach_object;


/// Convenience alias for `std::result::Result<T, Error>`
pub type Result<T> = ::std::result::Result<T, Error>;

/// Represents errors of the library
#[derive(Debug)]
pub enum Error {
    NoSuchArch,
    NoSuchSection,
    NoSuchAttribute,
    MachObject(mach_object::Error),
    Dwarf(gimli::Error),
    Io(io::Error),
}

impl From<mach_object::Error> for Error {
    fn from(err: mach_object::Error) -> Error {
        Error::MachObject(err)
    }
}

impl From<io::Error> for Error {
    fn from(err: io::Error) -> Error {
        Error::Io(err)
    }
}

impl From<gimli::Error> for Error {
    fn from(err: gimli::Error) -> Error {
        Error::Dwarf(err)
    }
}

impl ::std::error::Error for Error {
    fn description(&self) -> &str {
        match *self {
            Error::NoSuchArch => "no such architecture",
            Error::NoSuchSection => "no such section",
            Error::NoSuchAttribute => "no such attribute",
            Error::MachObject(ref err) => err.description(),
            Error::Io(ref err) => err.description(),
            Error::Dwarf(ref err) => err.description(),
        }
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match *self {
            Error::NoSuchArch => write!(f, "no such architecture"),
            Error::NoSuchSection => write!(f, "no such section"),
            Error::NoSuchAttribute => write!(f, "no such attribute"),
            Error::MachObject(ref err) => write!(f, "{}", err),
            Error::Io(ref err) => write!(f, "{}", err),
            Error::Dwarf(ref err) => write!(f, "{}", err),
        }
    }
}
