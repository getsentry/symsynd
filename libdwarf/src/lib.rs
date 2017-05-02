extern crate gimli;
extern crate memmap;
extern crate mach_object;
#[macro_use] extern crate if_chain;

mod read;
mod error;

pub use error::{Result, Error};
pub use read::DebugInfo;
