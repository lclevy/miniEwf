#minimal code to parse MBR and GPT 

from struct import Struct, pack
from collections import namedtuple
import sys
from binascii import unhexlify, hexlify, crc32

SECTOR_SIZE = 512

class Mbr:
  #MBR related data and functions
  MBR_SIZE = SECTOR_SIZE
  PART_TABLE_OFFSET = 0x1be
  PART_TABLE_SIZE = 4
  PARTTYPE_NOPART = 0
  PARTTYPE_EXFAT_NTFS = 7
  PARTTYPE_GPT = 0xee

  '''
  MBR Partition format

  offset,size,name, interpretation

  0   ubyte     boot flag        0x80 means bootable, 0 means not bootable
  1   3 bytes   CHS              obsolete
  4   ubyte     partition type   0x7 means NTFS, Exfat or ReFS
  5   3 bytes   CHS              obsolete
  8   ulong     1st sector       address of first sector
  12  ulong     size             size in sectors
  '''
  #https://docs.python.org/3/library/struct.html
  S_MBR_PART = Struct('<B3sB3sLL') #'<' means little endian
  NT_MBR_PART = namedtuple('mbr_part', 'flag chs_first type chs_last first_sector size')

  def __init__(self, mbrData):
    self.parse( mbrData )
    
  def parse(self, data):
    self.partitions = list()
    if data[Mbr.MBR_SIZE-2:Mbr.MBR_SIZE]!=b'\x55\xaa':
      print('not an MBR, missing 0x55aa')
      return None #we should raise an Exception. https://docs.python.org/fr/3.5/tutorial/errors.html
    else:
      for p in range(Mbr.PART_TABLE_SIZE):
        # by convention, _ is the variable name for ignored values in Python
        partition_nt = Mbr.NT_MBR_PART( *Mbr.S_MBR_PART.unpack_from(data, Mbr.PART_TABLE_OFFSET + p*Mbr.S_MBR_PART.size ) )
        if partition_nt.type != Mbr.PARTTYPE_NOPART:
          self.partitions.append( (p, partition_nt ) )
          
    self.gpt = False
    if len(self.partitions)==1:
      index, partition_nt = self.partitions[0]
      #print(partition_nt)
      if partition_nt.type==Mbr.PARTTYPE_GPT and partition_nt.first_sector==1 and partition_nt.size==0xffffffff:
        self.gpt = True


  def getPartitions(self):
    return self.partitions  
          
  def display(self):
    for p in self.partitions:
      index, partition_nt = p
      print('#%d boot=0x%02x type=0x%02x start=0x%08x size=0x%08x' % (index, partition_nt.flag, partition_nt.type, partition_nt.first_sector, partition_nt.size) )

def printHex(data, offset=0): 
  for i in range(0, len(data), 16):
    line = data[i:i+16]
    print('0x%03x: ' % (offset+i), end='')
    for j in range(0, 16, 4):
      print('%s' % hexlify(line[j:j+4]).decode(), end=' ')
    text = ''.join( ['.' if c<32 or c>127 else chr(c) for c in line] ) 
    print(text)

class Gpt:

  HEADER_SIZE = SECTOR_SIZE    
  HEADER_MAGIC = b'EFI PART'

  '''
  0 signature 
  8 version, L
  12 size, L
  16 CRC32, L
  20 L
  24 header LBA, Q
  '''
  S_HEADER_FORMAT = Struct('<8sLLLLQQQQ16sQLLL')
  assert S_HEADER_FORMAT.size == 92
  NT_HEADER_FORMAT = namedtuple('gpt_header', 'signature revision size header_crc reserved current_lba backup_lba first_lba last_lba guid partitions_lba part_count part_size partitions_crc')
  
  S_PARTITION_FORMAT = Struct('<16s16sQQQ72s') #72 because 36 UTF16LE
  assert S_PARTITION_FORMAT.size == 128
  NT_PARTITION_FORMAT = namedtuple('gpt_partition', 'type_guid guid first_lba last_lba flags name')

  EFI_TYPE = unhexlify('28732ac11ff8d211ba4b00a0c93ec93b')
  MICROSOFT_RESERVED_TYPE = unhexlify('16e3c9e35c0bb84d817df92df00215ae')
  BASIC_DATA_TYPE =  unhexlify('a2a0d0ebe5b9334487c068b6b72699c7')
  WINDOWS_RECOVERY_TYPE =  unhexlify('a4bb94ded106404da16abfd50179d6ac')
  
  HEADER_CRC_OFFSET = 16
  
  def __init__(self, gptHeader, currentLba=1):
    header_nt = Gpt.NT_HEADER_FORMAT (*Gpt.S_HEADER_FORMAT.unpack_from( gptHeader, 0 ) )
    #print(header_nt)
    assert header_nt.signature == Gpt.HEADER_MAGIC and header_nt.size == Gpt.S_HEADER_FORMAT.size and header_nt.current_lba == currentLba
    computedCrc = crc32( gptHeader[:Gpt.HEADER_CRC_OFFSET] + pack('L', 0) + gptHeader[Gpt.HEADER_CRC_OFFSET+4:header_nt.size] )
    if computedCrc != header_nt.header_crc:
      print( 'error: computed header CRC %08x is different than stored CRC %08x' % (computedCrc, header_nt.header_crc) )
    self.header = header_nt
    self.partitions = list()

  def parse_table(self, table):
    computedCrc = crc32(table)
    if computedCrc != self.header.partitions_crc:
      print( 'error: computed partitions CRC %08x is different than stored CRC %08x' % (computedCrc, self.header.partitions_crc) )
    for p in range(0, self.header.part_size*self.header.part_count, self.header.part_size):
      partition_nt = Gpt.NT_PARTITION_FORMAT( *Gpt.S_PARTITION_FORMAT.unpack_from( table, p ) )
      if partition_nt.type_guid != b'\x00'*16:
        self.partitions.append( (p//self.header.part_size, partition_nt) ) 
        #print(partition_nt)

  def display(self):
    print('    Type GUID                           GUID                                first    last     flags            name                ')
    for p in self.partitions:
      index, partition_nt = p
      name_end = min(partition_nt.name.find(b'\x00\x00'), 71)
      print('#%d: %s %s %8x %8x %16x %s' % (index, hexlify(partition_nt.type_guid), hexlify(partition_nt.guid), partition_nt.first_lba, partition_nt.last_lba, partition_nt.flags, partition_nt.name[:name_end+1].decode('UTF-16') ) )

if __name__ == '__main__':
  with open(sys.argv[1], 'rb') as f:
    mbr_data = f.read(SECTOR_SIZE)
    if mbr_data[3:11] == b'-FVE-FS-':
      print('bitlocker')
      sys.exit()
    mbr = Mbr(mbr_data)
    mbr.display()

    if mbr.gpt:
      f.seek(512)
      gpt_header = f.read(SECTOR_SIZE)
      gpt = Gpt(gpt_header, 1)
      
      
      
    
  