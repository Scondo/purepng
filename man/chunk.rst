.. $URL$
.. $Rev$

PNG: Chunk by Chunk
===================

The PNG specification defines 18 chunk types.  This document is intended
to help users who are interested in a particular PNG chunk type.  If you
have a particular PNG chunk type in mind, you can look here to see what
support PurePNG provides for it.

Critical Chunks
---------------

``IHDR``
^^^^^^^^

Generated automatically by PurePNG.  The ``IHDR`` chunk specifies image
size, colour model, bit depth, and interlacing.  All possible
(valid) combinations can be produced with suitable arguments to the
:class:`png.Writer` class.

``PLTE``
^^^^^^^^

Correctly handled when a PNG image is read.  Can be generated for a
colour type 3 image by using the ``palette`` argument to the
:class:`png.Writer` class.  PNG images with colour types other than 3 can
also have a ``PLTE`` chunk (a suggested palette); it is not currently
possible to add a ``PLTE`` chunk for these images using PyPNG.

``IDAT``
^^^^^^^^

Generated automatically from the pixel data presented to PurePNG.
Multiple ``IDAT`` chunks (of bounded size) can be generated by using
``chunk_limit`` argument to the :class:`png.Writer` class.

``IEND``
^^^^^^^^

Generated automatically.


Ancillary Chunks
----------------

``tRNS``
^^^^^^^^

Generated for most colour types when the ``transparent`` argument is
supplied to the :class:`png.Writer` to specify a transparent colour.  For
colour type 3, colour mapped images, a ``tRNS`` chunk will be generated
automatically from the ``palette`` argument when a palette with alpha
(opacity) values is supplied.

``cHRM``
^^^^^^^^

When reading a PNG image the ``cHRM`` chunk is converted to a tuples
``white_point`` (2-tuple of floating point values) and ``rgb_points``
(3-tuple of 2-tuple of floating point) in the ``info`` dictionary.
When writing, ``white_point`` and ``rgb_points`` arguments to the
:class:`png.Writer` class  or calling apropriate ``set_`` methods
generate a ``cHRM`` chunk (only both, single will be ignored).

``gAMA``
^^^^^^^^

When reading a PNG image the ``gAMA`` chunk is converted to a floating
point gamma value; this value is returned in the ``info`` dictionary:
``info['gamma']``.  When writing, the ``gamma`` argument to the
:class:`png.Writer` class will generate a ``gAMA`` chunk.

``iCCP``
^^^^^^^^

When reading a PNG image the ``iCCP`` chunk is saved as raw bytes and name.
These data returned in the ``info`` dictionary: ``info['icc_profile']``,
``info['icc_profile_name']``.
When writing, the ``icc_profile`` argument to the :class:`png.Writer` class
will generate a ``iCCP`` chunk, with name supplied in ``icc_profile_name``
argument or "ICC Profile" as default.


``sBIT``
^^^^^^^^

When reading a PNG image the ``sBIT`` chunk will make PyPNG rescale the
pixel values so that they all have the width implied by the ``sBIT``
chunk.  It is possible for a PNG image to have an ``sBIT`` chunk that
specifies 3 different values for the significant bits in each of the 3
colour channels.  In this case PyPNG only uses the largest value.  When
writing a PNG image, an ``sBIT`` chunk will be generated if need
according to the ``bitdepth`` argument specified.  Values other than 1,
2, 4, 8, or 16 will generate an ``sBIT`` chunk, as will values less than
8 for images with more than one plane.

``sRGB``
^^^^^^^^

When reading a PNG image the ``sRGB`` chunk is read to an integer value;
this value is returned in the ``info`` dictionary:
``info['rendering_intent']`` and can be compared to values like 
``png.PERCEPTUAL``.  When writing, the ``rendering_intent`` argument to the
:class:`png.Writer` class will generate a ``sRGB`` chunk.

``tEXt``
^^^^^^^^

When reading a PNG image the ``tEXt`` chunks are converted to a dictionary
of keywords and unicode values in the ``info`` dictionary: ``info['text']``.
When writing, the ``text`` argument with same dict to the :class:`png.Writer`
class or arguments with registered keywords names will generate ``tEXt`` chunks.

``zTXt``
^^^^^^^^

When reading a PNG image the ``zTXt`` chunks are converted to a dictionary
of keywords and unicode values in the ``info`` dictionary: ``info['text']``.
It's not possible to write ``zTXt`` chunsk for now, only ``tEXt`` will be
written with ``text`` keyword.

``iTXt``
^^^^^^^^

When reading append to ``text`` info same as  ``tEXt`` or ``zTXt``,
translated keyword and language tags ignored.

Keywords within ``text`` that does not fit latin-1 will be saved as ``iTXt``

``bKGD``
^^^^^^^^

When a PNG image is read, a ``bKGD`` chunk will add the ``background``
key to the ``info`` dictionary.  When writing a PNG image, a ``bKGD``
chunk will be generated when the ``background`` argument is used.

``hIST``
^^^^^^^^

Ignored when reading.  Not generated.

``pHYs``
^^^^^^^^

When reading a PNG image the ``pHYs`` chunk is converted to form
((<pixel_per_unit_x>, <pixel_per_unit_y>), <unit_is_meter>)
This tuple is returned in the ``info`` dictionary:
``info['resolution']``. 
When writing, the ``resolution`` argument to the :class:`png.Writer`
class will generate a ``pHYs`` chunk. Argument could be tuple same as
reading result, but also possible some usability modificatuion:

* if both resolutions are same it could be written as single number instead of tuple: (<pixel_per_unit_x>, <unit_is_meter>) 
* all three  parameters could be written in row: (<pixel_per_unit_x>, <pixel_per_unit_y>, <unit_is_meter>)
* instead of <unit_is_meter> bool it's possible to use some unit specification:
   1. omit this part if no unit specified ((<pixel_per_unit_x>, <pixel_per_unit_y>), )
   2. use text name of unit (300, 'i') 'i', 'cm' and 'm' supported for now.

``sPLT``
^^^^^^^^

Ignored when reading.  Not generated.

``tIME``
^^^^^^^^

When reading generate ``last_mod_time`` tuple which is time.structtime compatible.

:class:`png.Writer` have method :meth:`png.Writer.set_modification_time` which
could be used to specify ``tIME`` value or indicate that it should be calculated
as file writing time.

PNG Extensions Chunks
---------------------
See ftp://ftp.simplesystems.org/pub/png/documents/pngextensions.html

``oFFs``
^^^^^^^^^

Ignored when reading.  Not generated.

``pCAL``
^^^^^^^^

Ignored when reading.  Not generated.

``sCAL``
^^^^^^^^

Ignored when reading.  Not generated.

``gIFg``
^^^^^^^^

Ignored when reading.  Not generated.

``gIFx``
^^^^^^^^

Ignored when reading.  Not generated.

``sTER``
^^^^^^^^

Ignored when reading.  Not generated.

``dSIG``
^^^^^^^^

Ignored when reading.  Not generated.

``fRAc``
^^^^^^^^

Ignored when reading.  Not generated.

``gIFt``
^^^^^^^^

Ignored when reading.  Not generated.


Non-standard Chunks
-------------------

Generally it is not possible to generate PNG images with any other chunk
types.  When reading a PNG image, processing it using the chunk
interface, ``png.Reader.chunks``, will allow any chunk to be processed
(by user code).
