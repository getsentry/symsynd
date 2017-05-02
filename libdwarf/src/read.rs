use std::io;
use std::fs;
use std::ops::Deref;
use std::path::Path;
use std::ffi::{CStr, OsStr};
use std::os::unix::ffi::OsStrExt;

use gimli;
use memmap;
use mach_object::{OFile, LoadCommand, get_arch_from_flag};

use error::{Result, Error};


enum Backing<'a> {
    Mmap(memmap::Mmap),
    Buf(Vec<u8>),
    Slice(&'a [u8]),
}

impl<'a> Deref for Backing<'a> {
    type Target = [u8];

    fn deref(&self) -> &[u8] {
        match *self {
            Backing::Mmap(ref mmap) => unsafe { mmap.as_slice() },
            Backing::Buf(ref buf) => buf.as_slice(),
            Backing::Slice(slice) => slice,
        }
    }
}

fn cstr_as_path(s: &CStr) -> &Path {
    Path::new(OsStr::from_bytes(s.to_bytes()))
}

/// Convenient access to a subset of debug info relevant for symsynd
pub struct DebugInfo<'a> {
    backing: Backing<'a>,
    ofile: OFile,
}


impl<'a> DebugInfo<'a> {
    /// Opens a macho DWARF file from a path.
    pub fn open_path<P: AsRef<Path>>(p: P) -> Result<DebugInfo<'a>> {
        let f = fs::File::open(p)?;
        let mmap = memmap::Mmap::open(&f, memmap::Protection::Read)?;
        DebugInfo::from_backing(Backing::Mmap(mmap))
    }

    /// Opens a macho DWARF file from a vector.
    pub fn from_vec(vec: Vec<u8>) -> Result<DebugInfo<'a>> {
        DebugInfo::from_backing(Backing::Buf(vec))
    }

    /// Opens a macho DWARF file from a slice.
    pub fn from_slice(slice: &'a [u8]) -> Result<DebugInfo<'a>> {
        DebugInfo::from_backing(Backing::Slice(slice))
    }

    fn from_backing(backing: Backing<'a>) -> Result<DebugInfo<'a>> {
        let ofile = {
            let mut cursor = io::Cursor::new(&backing[..]);
            OFile::parse(&mut cursor)?
        };
        Ok(DebugInfo {
            backing: backing,
            ofile: ofile,
        })
    }

    fn get_arch(&self, cpu_name: &str) -> Result<(&OFile, &[u8])> {
        let arch = get_arch_from_flag(cpu_name).ok_or(Error::NoSuchArch)?;
        match self.ofile {
            OFile::FatFile { ref files, .. } => {
                for &(ref fat_arch, ref file) in files {
                    if fat_arch.cputype == arch.0 && fat_arch.cpusubtype == arch.1 {
                        let slice = &self.backing[fat_arch.offset as usize..
                                                  (fat_arch.offset + fat_arch.size) as usize];
                        return Ok((file, slice));
                    }
                }
            }
            OFile::MachFile { ref header, .. } => {
                if header.cputype == arch.0 && header.cpusubtype == arch.1 {
                    return Ok((&self.ofile, &self.backing[..]));
                }
            }
            _ => {}
        }
        Err(Error::NoSuchArch)
    }

    fn get_section(&self, cpu_name: &str, seg: &str, section: &str) -> Result<&[u8]> {
        let (file, slice) = self.get_arch(cpu_name)?;

        macro_rules! find_section {
            ($sections:expr) => {{
                for sect in $sections {
                    if sect.sectname == section && sect.segname == seg {
                        let subslice = &slice[sect.offset as usize..(sect.offset as usize) + sect.size];
                        return Ok(subslice);
                    }
                }
            }}
        }

        if let &OFile::MachFile { ref commands, .. } = file {
            for cmd in commands {
                match cmd.0 {
                    LoadCommand::Segment { ref sections, .. } => {
                        find_section!(&sections[..]);
                    }
                    LoadCommand::Segment64 { ref sections, .. } => {
                        find_section!(&sections[..]);
                    }
                    _ => {}
                }
            }
        }
        Err(Error::NoSuchSection)
    }

    /// Returns the compilation directory for a path.
    ///
    /// Given a CPU architecture and filename this returns the compilation
    /// directory of that file.  If the information is not available a
    /// `NoSuchArch` / `NoSuchAttribute` or `NoSuchSection` error will
    /// be returned.
    pub fn get_compilation_dir(&'a self, cpu_name: &str, filename: &Path)
        -> Result<&'a Path>
    {
        self.get_compilation_dir_cstr(cpu_name, filename).map(cstr_as_path)
    }

    /// Like `get_compilation_dir` but returns a `CStr`.
    pub fn get_compilation_dir_cstr(&'a self, cpu_name: &str, filename: &Path)
        -> Result<&'a CStr>
    {
        let info_slice = self.get_section(cpu_name, "__DWARF", "__debug_info")?;
        let abbrev_slice = self.get_section(cpu_name, "__DWARF", "__debug_abbrev")?;
        let strings = gimli::DebugStr::<gimli::LittleEndian>::new(
            self.get_section(cpu_name, "__DWARF", "__debug_str")?);

        let di = gimli::DebugInfo::<gimli::LittleEndian>::new(info_slice);
        let da = gimli::DebugAbbrev::<gimli::LittleEndian>::new(abbrev_slice);

        let mut units = di.units();
        while let Some(unit) = units.next()? {
            let abbrevs = unit.abbreviations(da)?;
            let mut entries = unit.entries(&abbrevs);
            while let Some((_, entry)) = entries.next_dfs()? {
                if_chain! {
                    if entry.tag() == gimli::DW_TAG_compile_unit;
                    if let Some(comp_dir) = entry.attr(gimli::DW_AT_comp_dir)?
                        .and_then(|attr| attr.string_value(&strings));
                    if let Some(name) = entry.attr(gimli::DW_AT_name)?
                        .and_then(|attr| attr.string_value(&strings));
                    if &cstr_as_path(comp_dir).join(cstr_as_path(name)) == filename;
                    then {
                        return Ok(comp_dir);
                    }
                }
            }
        }
        Err(Error::NoSuchAttribute)
    }
}
