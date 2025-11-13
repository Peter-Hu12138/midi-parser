import dataclasses
import _io

@dataclasses.dataclass
class Event:
    timestamp: float
    pitch: int
    instrument: int
    velocity: int
    duration: float

# Pre: pointer of file is right before the variable len to be read
# Post: the length specified, and pointer just after variable length segment
def parse_variable_length(file_obj: _io.BufferedReader) -> int:
    leftmost_byte = int.from_bytes(file_obj.read(1))
    buffer = leftmost_byte & 0x7F
    while leftmost_byte >> 7 == 1:
        leftmost_byte = int.from_bytes(file_obj.read(1))
        buffer = buffer << 7 + leftmost_byte & 0x7F
    return buffer

# Post: the returned list is ordered in chronological order 
def parse_midi(file_name: str) -> list[Event]:
    # might need to govern channel
    output = []

    midi_file = open("Columns_Original.mid","rb")
    header_identifier = midi_file.read(4)
    header_length = int.from_bytes(midi_file.read(4))
    format = int.from_bytes(midi_file.read(2))
    num_tracks = int.from_bytes(midi_file.read(2))
    divisions = int.from_bytes(midi_file.read(2))

    if divisions >> 7 == 1:
        raise ValueError("SMPTE timing not supported")
    if format == 2:
        raise ValueError("multiple song file format not supported")
    
    buffer = int.from_bytes(midi_file.read(4))
    while buffer:
        if buffer == 0x4d54726b: # "mtrk"
            # process a chunk
            track_len = int.from_bytes(midi_file.read(4))
            starting_byte = midi_file.tell()
            while midi_file.tell() - starting_byte < track_len:
                delta_time = parse_variable_length(midi_file)
                status = int.from_bytes(midi_file.read(1))
                if status & 0x80 == 0: # running status
                    # redo reading, this is note!
                    midi_file.seek(-1, 1)
                else:
                    # this is event!
                    event_type = status >> 4

                
                # if midi event
                if event_type != 0xF:
                    channel_number = status & 0xF
                    match event_type:
                        case 0x8:
                            # note off
                            note = int.from_bytes(midi_file.read(1))
                            velocity = int.from_bytes(midi_file.read(1))
                        case 0x9:
                            # note on
                            note = int.from_bytes(midi_file.read(1))
                            velocity = int.from_bytes(midi_file.read(1))
                        case 0xA:
                            # polyphonic key pressure
                            note = int.from_bytes(midi_file.read(1))
                            pressure = int.from_bytes(midi_file.read(1))
                        case 0xB:
                            # Code to execute if pattern matches AND condition is true
                            control = int.from_bytes(midi_file.read(1))
                            value = int.from_bytes(midi_file.read(1))
                        case 0xC:
                            # program (intrument change)
                            program = int.from_bytes(midi_file.read(1))
                        case 0xD:
                            # pressure
                            pressure = int.from_bytes(midi_file.read(1))
                        case 0xE:
                            # pitch wheel change
                            lsb = int.from_bytes(midi_file.read(1))
                            msb = int.from_bytes(midi_file.read(1))
                            change = msb << 8 + lsb
                        case _: # Default case (catch-all)
                            # Code to execute if no other patterns match
                            raise ValueError("unexpected event type")
                else:
                    match status & 0xF:
                        case 0x0 | 0x7:
                            print("system exclusive event, ignoring due to no implementation")
                            sysex_len = parse_variable_length(midi_file)
                            midi_file.read(sysex_len)
                        case 0x1:
                            print("unimplemented timing system, ignoring")
                            midi_file.read(1)
                        case 0x2:
                            # song position pointer
                            lsb = int.from_bytes(midi_file.read(1))
                            msb = int.from_bytes(midi_file.read(1))
                            pointer = msb << 8 + lsb
                        case 0x3:
                            song = int.from_bytes(midi_file.read(1))
                            raise ValueError("unimplemented song select")
                        case 0x6:
                            # tune request
                            pass
                        case 0xF:
                            # meta events
                            type = int.from_bytes(midi_file.read(1))
                            meta_event_len = parse_variable_length(midi_file)
                            if 1 <= type <= 7:
                                text = midi_file.read(meta_event_len).decode()
                                print(f"text data:{text}")
                            match type:
                                case 0x0 | 0x20 | 0x54:
                                    content = midi_file.read(
                                        meta_event_len
                                        )
                                    print(f"ignoring unimplemented meta messages {content}")
                                case 0x2f:
                                    # end of track
                                    # fast forward to next mtrk
                                    break
                                case 0x51:
                                    # set tempo
                                    tempo = int.from_bytes(
                                        midi_file.read(meta_event_len)
                                    )
                                case 0x58:
                                    # time signature
                                    num = int.from_bytes(midi_file.read(1))
                                    den = 2 ** int.from_bytes(midi_file.read(1))
                                    clocks = int.from_bytes(midi_file.read(1))
                                    useless = int.from_bytes(midi_file.read(1))

                        case _:
                            raise ValueError(f"undefined event: {hex(status)}")
            buffer = 0
        else:
            buffer = ((buffer & 0x00ffffff) << 8) + int.from_bytes(midi_file.read(1))





parse_midi("Columns_Original.mid")

