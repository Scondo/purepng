#!/usr/bin/env python
"""
International Color Consortium Profile

Tools for manipulating ICC profiles.

An ICC profile can be extracted from a PNG image (iCCP chunk).


Non-standard ICCP tags.

Apple use some (widespread but) non-standard tags.  These can be
displayed in Apple's ColorSync Utility.
- 'vcgt' (Video Card Gamma Tag).  Table to load into video
   card LUT to apply gamma.
- 'ndin' Apple display native information.
- 'dscm' Apple multi-localized description strings.
- 'mmod' Apple display make and model information.


References
[ICC 2001] ICC Specification ICC.1:2001-04 (Profile version 2.4.0)
[ICC 2004] ICC Specification ICC.1:2004-10 (Profile version 4.2.0.0)
"""
import struct
import warnings

try:
    exec("from . import png", globals(), locals())
except (SyntaxError, ValueError):
    # On Python < 2.5 relative import cause syntax error
    # Also works when running outside of package
    import png


# Utils
def group(s, n):
    """Repack iterator items into groups"""
    # See http://www.python.org/doc/2.6/library/functions.html#zip
    return zip(*[iter(s)] * n)


class Profile(object):

    """An International Color Consortium Profile (ICC Profile)."""

    def __init__(self):
        self.rawtagtable = None
        self.rawtagdict = {}
        self.d = dict()  # Dict of basic properties
        self.tag = dict()  # Dict of tags
        self.name = None

    def fromFile(self, inp, name='<unknown>'):
        # See [ICC 2004]
        profile = inp.read(128)
        if len(profile) < 128:
            raise png.FormatError("ICC Profile is too short.")
        size, = struct.unpack('>L', profile[:4])
        profile += inp.read(size - len(profile))
        return self.fromString(profile, name)

    def fromString(self, profile, name='<unknown>'):
        self.d = dict()
        d = self.d
        if len(profile) < 128:
            raise png.FormatError("ICC Profile is too short.")
        d.update(dict(
          zip(['size', 'preferredCMM', 'version',
               'profileclass', 'colourspace', 'pcs'],
              struct.unpack('>L4sL4s4s4s', profile[:24]))))
        if len(profile) < d['size']:
            warnings.warn(
              'Profile size declared to be %d, but only got %d bytes' %
              (d['size'], len(profile)))
        d['version'] = '%08x' % d['version']
        d['created'] = readICCdatetime(profile[24:36])
        d.update(dict(
          zip(['acsp', 'platform', 'flag', 'manufacturer', 'model'],
              struct.unpack('>4s4s3L', profile[36:56]))))
        if d['acsp'] != png.strtobytes('acsp'):
            warnings.warn('acsp field not present (not an ICC Profile?).')
        d['deviceattributes'] = profile[56:64]
        d['intent'], = struct.unpack('>L', profile[64:68])
        d['pcsilluminant'] = readICCXYZNumber(profile[68:80])
        d['creator'] = profile[80:84]
        d['id'] = profile[84:100]
        ntags, = struct.unpack('>L', profile[128:132])
        d['ntags'] = ntags
        fmt = '4s2L' * ntags
        # tag table
        tt = struct.unpack('>' + fmt, profile[132:132 + 12 * ntags])
        tt = group(tt, 3)

        # Could (should) detect 2 or more tags having the same sig.  But
        # we don't.  Two or more tags with the same sig is illegal per
        # the ICC spec.

        # Convert (sig,offset,size) triples into (sig,value) pairs.
        rawtag = list(map(lambda x: (x[0], profile[x[1]:x[1] + x[2]]), tt))
        self.rawtagtable = rawtag
        self.rawtagdict = dict(rawtag)
        tag = dict()
        # Interpret the tags whose types we know about
        for sig, v in rawtag:
            sig = png.bytestostr(sig)
            if sig in tag:
                warnings.warn("Duplicate tag %r found.  Ignoring." % sig)
                continue
            v = ICCdecode(v)
            if v is not None:
                tag[sig] = v
        self.tag = tag
        self.name = name
        return self

    def greyInput(self):
        """
        Adjust ``self.d`` dictionary for greyscale input device.

        ``profileclass`` is 'scnr', ``colourspace`` is 'GRAY',
        ``pcs`` is 'XYZ '.
        """
        self.d.update(dict(profileclass='scnr',
          colourspace='GRAY', pcs='XYZ '))
        return self

    def maybeAddDefaults(self):
        if self.rawtagdict:
            return
        self._addTags(cprt='Copyright unknown.',
                      desc='created by $URL$ $Rev$',
                      wtpt=D50,
                      )

    def addTags(self, **k):
        self.maybeAddDefaults()
        self._addTags(**k)

    def _addTags(self, **k):
        """Helper for :meth:`addTags`."""
        for tag, thing in k.items():
            if not isinstance(thing, (tuple, list)):
                thing = (thing,)
            typetag = defaulttagtype[tag]
            self.rawtagdict[tag] = encode(typetag, *thing)
        return self

    def asString(self):
        """Bytestring representation of ICC Profile"""
        if not self.rawtagtable:
            self.rawtagtable = self.rawtagdict.items()
        res = self.makeHeader()
        res += tagblock(self.rawtagtable)
        return res

    def __str__(self):
        """Provide string representation for Python < 3 or special cases"""
        return png.strtobytes(self.asString())

    def __bytes__(self):
        """Bytestring representation of ICC Profile"""
        return self.asString()

    def write(self, out):
        """Write ICC Profile to the file."""
        s = self.asString()
        out.write(struct.pack('>L', len(s) + 4))
        out.write(s)
        out.flush()
        return self

    def makeHeader(self):
        """
        Costruct header of ICC Profile

        Add default values to the instance's `d` dictionary, then
        return string contains header.
        """

        def ensurebytes(string):
            """If `string` is `str` type - convert it to bytes"""
            if isinstance(string, str):
                return png.strtobytes(string)
            else:
                return string

        z = png.zerobyte * 4
        defaults = dict(preferredCMM=z,
                        version='02000000',
                        profileclass=z,
                        colourspace=z,
                        pcs='XYZ ',
                        created=writeICCdatetime(),
                        acsp='acsp',
                        platform=z,
                        flag=0,
                        manufacturer=z,
                        model=0,
                        deviceattributes=0,
                        intent=0,
                        pcsilluminant=encodefuncs['XYZ'](*D50),
                        creator=z,
                        )
        for k, v in defaults.items():
            self.d.setdefault(k, v)

        hl = [self.d[k] for k in
              ('preferredCMM', 'version', 'profileclass', 'colourspace',
               'pcs', 'created', 'acsp', 'platform', 'flag',
               'manufacturer', 'model', 'deviceattributes', 'intent',
               'pcsilluminant', 'creator')]
        hl = [ensurebytes(it) for it in hl]
        # Convert to struct.pack input
        hl[1] = int(hl[1], 16)

        res = struct.pack('>4sL4s4s4s12s4s4sL4sLQL12s4s', *hl)
        res += png.zerobyte * 44
        return res


def encodefuns():
    """
    Returns a dictionary mapping ICC type signature to encoding function.

    Each function returns a bytestring comprising the content of
    the encoded value.  To form the full value, the type signature and the 4
    zero bytes should be prefixed (8 bytes).
    """
    def desc(ascii):
        """
        Return textDescription type [ICC 2001] 6.5.17.

        The ASCII part is filled in with the string `ascii`,
        the Unicode and ScriptCode parts are empty.
        """
        ascii = png.strtobytes(ascii) + png.zerobyte
        l = len(ascii)
        return struct.pack('>L%ds2LHB67s' % l,
                           l, ascii, 0, 0, 0, 0, png.strtobytes(''))

    def text(ascii):
        """Return textType [ICC 2001] 6.5.18."""
        return ascii + png.zerobyte

    def curv(f=None, n=256):
        """
        Return a curveType, [ICC 2001] 6.5.3.

        If no arguments are  supplied then a TRC for a linear response
        is generated (no entries).
        If an argument is supplied and it is a number (for *f* to be a
        number it  means that ``float(f)==f``) then a TRC for that
        gamma value is generated.
        Otherwise `f` is assumed to be a function that maps [0.0, 1.0] to
        [0.0, 1.0]; an `n` element table is generated for it.
        """
        if f is None:
            return struct.pack('>L', 0)
        try:
            if float(f) == f:
                return struct.pack('>LH', 1, int(round(f * 2 ** 8)))
        except (TypeError, ValueError):
            pass
        assert n >= 2
        table = []
        M = float(n - 1)
        for i in range(n):
            x = i / M
            table.append(int(round(f(x) * 65535)))
        return struct.pack('>L%dH' % n, n, *table)

    def XYZ(*l):
        return struct.pack('>3l', *map(fs15f16, l))

    return locals()

encodefuncs = encodefuns()
# Tag type defaults.
# Most tags can only have one or a few tag types.
# When encoding, we associate a default tag type with each tag so that
# the encoding is implicit.
defaulttagtype = dict(
  A2B0='mft1',
  A2B1='mft1',
  A2B2='mft1',
  bXYZ='XYZ',
  bTRC='curv',
  B2A0='mft1',
  B2A1='mft1',
  B2A2='mft1',
  calt='dtim',
  targ='text',
  chad='sf32',
  chrm='chrm',
  cprt='desc',
  crdi='crdi',
  dmnd='desc',
  dmdd='desc',
  devs='',
  gamt='mft1',
  kTRC='curv',
  gXYZ='XYZ',
  gTRC='curv',
  lumi='XYZ',
  meas='',
  bkpt='XYZ',
  wtpt='XYZ',
  ncol='',
  ncl2='',
  resp='',
  pre0='mft1',
  pre1='mft1',
  pre2='mft1',
  desc='desc',
  pseq='',
  psd0='data',
  psd1='data',
  psd2='data',
  psd3='data',
  ps2s='data',
  ps2i='data',
  rXYZ='XYZ',
  rTRC='curv',
  scrd='desc',
  scrn='',
  tech='sig',
  bfd='',
  vued='desc',
  view='view',
)


def encode(tsig, *l):
    """
    Encode a Python value as an ICC type.

    `tsig` is the type signature to (the first 4 bytes of
    the encoded value, see [ICC 2004] section 10.
    """
    if tsig not in encodefuncs:
        raise "No encoder for type %r." % tsig
    v = encodefuncs[tsig](*l)
    # Padd tsig out with spaces (and ensure it is bytes).
    tsig = (png.strtobytes(tsig + '   '))[:4]
    return tsig + png.zerobyte * 4 + v


def tagblock(tag):
    """
    Serialize block of tags

    `tag` should be a list of (*signature*, *element*) pairs, where
    *signature* (the key) is a length 4 string, and *element* is the
    content of the tag element (another string).

    The entire tag block (consisting of first a table and then the
    element data) is constructed and returned as a string.
    """
    n = len(tag)
    tablelen = 12 * n

    # Build the tag table in two parts.  A list of 12-byte tags, and a
    # string of element data.  Offset is the offset from the start of
    # the profile to the start of the element data (so the offset for
    # the next element is this offset plus the length of the element
    # string so far).
    offset = 128 + tablelen + 4
    # The table.  As a string.
    table = png.strtobytes('')
    # The element data
    element = png.strtobytes('')
    for k, v in tag:
        table += struct.pack('>4s2L', png.strtobytes(k), offset + len(element),
                             len(v))
        element += v
    return struct.pack('>L', n) + table + element


def fs15f16(x):
    """Convert float to ICC s15Fixed16Number (as a Python ``int``)."""

    return int(round(x * 2 ** 16))


# See [ICC 2001] A.1
D50 = (0.9642, 1.0000, 0.8249)  # D50 illuminant as an (X,Y,Z) triple


def blackshift(m):
    """
    Produce a function to shift black (base) point.

    Return a function that maps all values from [0.0,m] to 0, and maps
    the range [m,1.0] into [0.0, 1.0] linearly.
    """

    m = float(m)

    def f(x):
        if x <= m:
            return 0.0
        return (x - m) / (1.0 - m)
    return f


def writeICCdatetime(t=None):
    """
    `t` should be a gmtime tuple (as returned from ``time.gmtime()``).

    If not supplied, the current time will be used.
    Return an ICC dateTimeNumber in a 12 byte string.
    """
    import time
    if t is None:
        t = time.gmtime()
    return struct.pack('>6H', *t[:6])


def readICCdatetime(s):
    """Convert from 12 byte ICC representation of dateTimeNumber to
    ISO8601 string. See [ICC 2004] 5.1.1"""
    return '%04d-%02d-%02dT%02d:%02d:%02dZ' % struct.unpack('>6H', s)


def readICCXYZNumber(s):
    """Convert from 12 byte ICC representation of XYZNumber to (x,y,z)
    triple of floats.  See [ICC 2004] 5.1.11"""
    return s15f16l(s)


def s15f16l(s):
    """Convert sequence of ICC s15Fixed16 to list of float."""

    # Note: As long as float has at least 32 bits of mantissa, all
    # values are preserved.
    n = len(s) // 4
    t = struct.unpack('>%dl' % n, s)
    return map((2**-16).__mul__, t)


# Several types and their byte encodings are defined by [ICC 2004]
# section 10.  When encoded, a value begins with a 4 byte type
# signature.  We use the same 4 byte type signature in the names of the
# Python functions that decode the type into a Pythonic representation.
def ICCdecode(s):
    """Take an ICC encoded tag, and dispatch on its type signature
    (first 4 bytes) to decode it into a Python value.  Pair (*sig*,
    *value*) is returned, where *sig* is a 4 byte string, and *value* is
    some Python value determined by the content and type.
    """
    sig = png.bytestostr(s[0:4].strip())
    f = dict(text=RDtext,
             XYZ=RDXYZ,
             curv=RDcurv,
             vcgt=RDvcgt,
             sf32=RDsf32,
             )
    if sig not in f:
        return None
    return (sig, f[sig](s))


def RDXYZ(s):
    """Convert ICC XYZType to rank 1 array of trimulus values."""

    # See [ICC 2001] 6.5.26
    assert s[0:4] == png.strtobytes('XYZ ')
    return readICCXYZNumber(s[8:])


def RDsf32(s):
    """Convert ICC s15Fixed16ArrayType to list of float."""

    # See [ICC 2004] 10.18
    assert s[0:4] == png.strtobytes('sf32')
    return s15f16l(s[8:])


# TODO: Unused
def RDmluc(s):
    """
    Convert ICC multiLocalizedUnicodeType.

    This types encodes several strings together with a language/country
    code for each string.  A list of (*lc*, *string*) pairs is returned
    where *lc* is the 4 byte language/country code, and *string* is the
    string corresponding to that code.  It seems unlikely that the same
    language/country code will appear more than once with different
    strings, but the ICC standard does not prohibit it.
    """
    # See [ICC 2004] 10.13
    assert s[0:4] == png.strtobytes('mluc')
    n, sz = struct.unpack('>2L', s[8:16])
    assert sz == 12
    record = []
    for _ in range(n):
        lc, l, o = struct.unpack('4s2L', s[16 + 12 * n:28 + 12 * n])
        record.append(lc, s[o:o + l])
    # How are strings encoded?
    return record


def RDtext(s):
    """Convert ICC textType to Python string."""

    # Note: type not specified or used in [ICC 2004], only in older
    # [ICC 2001].
    # See [ICC 2001] 6.5.18
    assert s[0:4] == png.strtobytes('text')
    return s[8:-1]


def RDcurv(s):
    """Convert ICC curveType."""

    # See [ICC 2001] 6.5.3
    assert s[0:4] == png.strtobytes('curv')
    count, = struct.unpack('>L', s[8:12])
    if count == 0:
        return dict(gamma=1)
    table = struct.unpack('>%dH' % count, s[12:])
    if count == 1:
        return dict(gamma=table[0] * 2 ** -8)
    return table


def RDvcgt(s):
    """Convert Apple CMVideoCardGammaType."""

    # See
    # http://developer.apple.com/documentation/GraphicsImaging/Reference/
    #         ColorSync_Manager/Reference/reference.html#//apple_ref/c/
    #         tdef/CMVideoCardGammaType
    assert s[0:4] == png.strtobytes('vcgt')
    tagtype, = struct.unpack('>L', s[8:12])
    if tagtype != 0:
        return s[8:]
    if tagtype == 0:
        # Table.
        _, count, size = struct.unpack('>3H', s[12:18])
        if size == 1:
            fmt = 'B'
        elif size == 2:
            fmt = 'H'
        else:
            return s[8:]
        l = len(s[18:]) // size
        t = struct.unpack('>%d%s' % (l, fmt), s[18:])
        t = group(t, count)
        return size, t
    return s[8:]


# CLI Implementation
def iccpout(out, inp, **kwargs):
    """Extract ICC Profile from PNG file `inp` to the file `out`."""
    out.write(png.Reader(file=inp).read()[3]['icc_profile'][1])


def iccpadd(inp, out, addfile, **kwargs):
    """Add ICC Profile to png file and write result to file `out`"""
    iccfile = open(addfile, 'rb')
    pix, meta = png.Reader(file=inp).read()[2:]
    meta['icc_profile'] = iccfile.read()
    iccfile.close()
    w = png.Writer(**meta)
    w.write(out, pix)


def iccpview(inp, out, **kwargs):
    """Parse ICC Profile of png file and write result to file `out`"""
    meta = png.Reader(file=inp).read()[3]

    def analyze(profile):
        yield 'Header:\n'
        for pair in profile.d.items():
            yield '%s: %s\n' % pair
        yield 'Tags:\n'
        for pair in profile.tag.items():
            yield '%s: %s\n' % pair

    profile = Profile()
    profile.fromString(meta['icc_profile'][1], meta['icc_profile'][0])
    out.writelines(map(png.strtobytes, analyze(profile)))


def mkgrey(out, **kwargs):
    it = Profile().greyInput()
    black = kwargs.get('black', 0.07)
    it.addTags(kTRC=blackshift(black))
    it.write(out)


def main(argv=None):
    import sys
    from getopt import getopt

    def funcmode(mode):
        """Determine function by mode"""
        if mode == 'export':
            return iccpout
        elif mode == 'add':
            return iccpadd
        elif mode == 'view':
            return iccpview
        elif mode == 'mkgrey':
            return mkgrey

    if argv is None:
        argv = sys.argv
    argv = argv[1:]
    opt, arg = getopt(argv, 'o:m:a:')
    cfg = dict(mode='export')
    if len(arg) > 0:
        cfg['inp'] = open(arg[0], 'rb')
    else:
        cfg['inp'] = sys.stdin
    for o, v in opt:
        if o == '-o':
            if v in ('-', 'stdout'):
                cfg['out'] = sys.stdout
            else:
                cfg['out'] = open(v, 'wb')
            funcmode(cfg['mode'])(**cfg)
            if v not in ('-', 'stdout'):
                cfg['out'].close()
        elif o == '-m':
            cfg['mode'] = v
        elif o == '-a':
            cfg['addfile'] = v
    if len(arg) > 0:
        cfg['inp'].close()

if __name__ == '__main__':
    main()
