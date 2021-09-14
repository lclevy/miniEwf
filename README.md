# miniEwf
Minimal EWF "driver" in pure Python, to depict inner working of EWF (Evidence Witness Forensic) / Encase file format.

Code written as example for this article in French magazine MISC MAG #117 : https://connect.ed-diamond.com/misc/misc-117/description-du-format-de-stockage-forensique-encase-ewf

### Usage as a cli tool

```
>python ewf.py -h
usage: ewf.py [-h] [-v VERBOSE] [-c] imagefile

positional arguments:
  imagefile   image file

optional arguments:
  -h, --help  show this help message and exit
  -v VERBOSE  verbose level
  -c          verify adler32 checksums
```

on an USB dump in 3 segments : usb.E01 to usb.E03 :

 ```
 >python ewf.py -v 1 usb.E01
 usb.E01
 header(signature=b'EVF\t\r\n\xff\x00', one=1, segment_num=1, zero=0)
 0x00000059: type:b'header2\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:fe ize:f1
 0x000000fe: type:b'header2\x00\x00\x00\x00\x00\x00\x00\x00\x00' ext:1ef size:f1
 0x000001ef: type:b'header\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:28a size:9b
 0x0000028a: type:b'volume\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:6f2 size:468
 0x000006f2: type:b'sectors\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:5db7e7cf size:5db7e0dd
 0x5db7e7cf: type:b'table\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:5dbbb3d7 size:3cc08
 0x5dbbb3d7: type:b'table2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:5dbf7fdf size:3cc08
 0x5dbf7fdf: type:b'next\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:5dbf7fdf size:0
 usb.E02
 header(signature=b'EVF\t\r\n\xff\x00', one=1, segment_num=2, zero=0)
 0x00000059: type:b'data\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:475 size:468
 0x00000475: type:b'sectors\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:5db993ee size:5db98f79
 0x5db993ee: type:b'table\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:5dbcb42a size:3203c
 0x5dbcb42a: type:b'table2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:5dbfd466 size:3203c
 0x5dbfd466: type:b'next\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:5dbfd466 size:0
 usb.E03
 header(signature=b'EVF\t\r\n\xff\x00', one=1, segment_num=3, zero=0)
 0x00000059: type:b'data\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:475 size:468
 0x00000475: type:b'sectors\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:96134e3 size:961306e
 0x096134e3: type:b'table\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:96183d7 size:4ef4
 0x096183d7: type:b'table2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:961d2cb size:4ef4
 0x0961d2cb: type:b'hash\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:961d33b size:70
 0x0961d33b: type:b'done\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' next:961d33b size:0
 chunk_count:0x1ce80, sectors_per_chunk:0x40, bytes_per_sector:0x200, sector_count:0x73a000
 md5: b'4e009a14d2f73b7bbc52a5ea3a1b5105'
 segment #1, filename: usb.E01
   chunks count: 62184 (including uncompressed:22777, 36.63%)
   data offsets: first:0x73e last:0x5db767cb
   absolute chunk number ranges (0, 62183)
   end_of_sectors: 0x5db7e7cf
 segment #2, filename: usb.E02
   chunks count: 51189 (including uncompressed:15321, 29.93%)
   data offsets: first:0x4c1 last:0x5db914ba
   absolute chunk number ranges (62184, 113372)
   end_of_sectors: 0x5db993ee
 segment #3, filename: usb.E03
   chunks count: 5027 (including uncompressed:2896, 57.61%)
   data offsets: first:0x4c1 last:0x960b4df
   absolute chunk number ranges (113373, 118399)
   end_of_sectors: 0x96134e3
 ```

 

### as a Python class

 you can use read() and seek() inside EWF dump:

```
from part import Mbr, Gpt #parse MBR and GPT partitions tables

ewf = Ewf( args.imagefile, args.checksum, args.verbose )
ewf.display_properties()
  
#read first sector
data = ewf.read(512)
mbr = Mbr(data)
mbr.display()

if mbr.gpt:
  index, partition = mbr.partitions[0]
   
  #read GPT header
  ewf.seek( partition.first_sector*512 )
  gpt_header = ewf.read( 512 )
  gpt = Gpt( gpt_header )
    
  #read GPT partitions table
  ewf.seek(gpt.header.partitions_lba * 512)
  gptPart = ewf.read(gpt.header.part_count * gpt.header.part_size)
  gpt.parse_table( gptPart )
  gpt.display()
    
  for p in gpt.partitions:
    index, partitions = p
    ewf.seek( partitions.first_lba * 512 )
    vbr = ewf.read(512)
    printHex( vbr[:16*6] )
    print()

  #compute hash value of the image, using read() function
  print('re-computing original md5...')
  print( hexlify( compute_image_hash2( ewf, md5() ) ) )
```

 

MBR analysis of the dump is show, first partition data is shown (output of "mbr.display()" line above):

```
#0 boot=0x80 type=0x0c start=0x00002678 size=0x00737988
```



Output of line "print( hexlify( compute_image_hash2( ewf, md5() ) ) )"

b'4e009a14d2f73b7bbc52a5ea3a1b5105'

with compute_image_hash2() function as:

```
BUFFER_SIZE = 0x40*512-1 #to assess read()
def compute_image_hash2(ewf, md): #using read()
  ewf.seek(0)
  
  data = ewf.read( BUFFER_SIZE )
  while len(data) > 0:
    md.update( data )
    if len(data) < BUFFER_SIZE: #detect short read
      return md.digest()
    data = ewf.read( BUFFER_SIZE )
  return md.digest()
```

Conclusion : recomputation of original md5 using ewf.read() is working and identifical to md5 value in metadata (from hash section)

### Limitations

- seek() need further testing
- It is slow, do not expect C++ performance, use https://github.com/libyal/libewf instead.
- tested with FTK Imager and ewfacquire dumps

### References

- E01 Compression Format, ASRDATA, around 2002, http://www.asrdata.com/whitepaper-html/
- libevf code source, Michael Cohen, 2008, https://github.com/py4n6/pyflag/blob/master/src/lib/libevf.c
- EWF specification, Joachim Metz, 2006-2020, [https://github.com/libyal/libewf/blob/main/documentation/Expert%20Witness%20Compression%20Format%20(EWF).asciidoc](https://github.com/libyal/libewf/blob/main/documentation/Expert%20Witness%20Compression%20Format%20(EWF).asciidoc)

