import dataclasses
import _io

@dataclasses.dataclass
class Event:
    timestamp: float
    pitch: int
    instrument: int
    velocity: int
    duration: float
    volume: int


@dataclasses.dataclass
class Channel:
    instrument: int
    volume: int
    ongoing_events: list[Event]
    closed_events: list[Event]

    def note_on_event(self, start_timestamp: float, pitch: int, velocity: int):
        evt = Event(start_timestamp, pitch, self.instrument, velocity, -1, self.volume)
        self.ongoing_events.append(evt)

    def note_off_event(self, end_timestamp: float, pitch: int):
        for i in range(len(self.ongoing_events)):
            evt = self.ongoing_events[i]
            if evt.pitch == pitch:
                evt.duration = end_timestamp - evt.timestamp
                self.closed_events.append(self.ongoing_events.pop(i))
                return 
        raise ValueError("unmatched note off event!")
    
    def pitch_bend(self, pitchbend):
        sensitivity = 2
        change = ((pitchbend - 8192) / 8192) * sensitivity

    def set_volume(self, timestamp: float, new_vol: int):
        self.volume = new_vol
        for i in range(len(self.ongoing_events)):
            ongoing_evt = self.ongoing_events.pop(i)
            ongoing_evt.duration = (timestamp - ongoing_evt.timestamp) + 0.001
            self.closed_events.append(ongoing_evt)
            self.ongoing_events.append(Event(
                timestamp, 
                ongoing_evt.pitch,
                self.instrument,
                ongoing_evt.velocity,
                -1,
                self.volume
                ))
            



# Pre: pointer of file is right before the variable len to be read
# Post: return the length specified, and pointer points at just after variable length segment
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
    midi_events = []
    midi_channels = [Channel(0, 100, [], []) for i in range(16)]

    midi_file = open(file_name,"rb")
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
            timestamp = 0
            track_len = int.from_bytes(midi_file.read(4))
            starting_byte = midi_file.tell()
            while midi_file.tell() - starting_byte < track_len:
                delta_time = parse_variable_length(midi_file)
                try:
                    timestamp += delta_time * tick
                except UnboundLocalError:
                    timestamp = 0
                try:
                    next_byte = int.from_bytes(midi_file.peek(1)[:1])
                    if next_byte & 0x80:
                        # this is event! assign to status
                        status = int.from_bytes(midi_file.read(1))
                    else:
                        status = running_status
                except UnboundLocalError:
                    raise UnboundLocalError("midi file has an invalid running status pattern - having one before any channel event")

                # status is the actual status byte for this event
                # accounting for running status
                event_type = status >> 4
                channel_number = status & 0xF
            

                # if midi event
                if event_type != 0xF:
                    running_status = status
                    match event_type:
                        case 0x8:
                            # note off
                            note = int.from_bytes(midi_file.read(1))
                            velocity = int.from_bytes(midi_file.read(1))
                            midi_channels[channel_number].note_off_event(timestamp, note)
                        case 0x9:
                            # note on
                            note = int.from_bytes(midi_file.read(1))
                            velocity = int.from_bytes(midi_file.read(1))
                            if velocity == 0:
                                try:
                                    midi_channels[channel_number].note_off_event(timestamp, note)
                                except ValueError as e:
                                    print("no match was found", e)
                            else:
                                midi_channels[channel_number].note_on_event(timestamp, note, velocity)
                        case 0xA:
                            # polyphonic key pressure
                            note = int.from_bytes(midi_file.read(1))
                            pressure = int.from_bytes(midi_file.read(1))
                            print(f"ignoring event: polyphonic key pressure note: {note} pressure: {pressure}")
                        case 0xB:
                            control = int.from_bytes(midi_file.read(1))
                            value = int.from_bytes(midi_file.read(1))
                            match control:
                                case 7:
                                    midi_channels[channel_number].set_volume(timestamp, value)
                                    print(f"new volume: {value}")
                                case 100:
                                    control_lsb = value
                                case 101:
                                    control_msb = value
                                case _:
                                    print(f"ignoring event: controller: control: {control} value: {value}")

                        case 0xC:
                            # program (intrument change)
                            program = int.from_bytes(midi_file.read(1))
                            midi_channels[channel_number].instrument = program
                            print(f"program change to {program}!")
                        case 0xD:
                            # pressure
                            pressure = int.from_bytes(midi_file.read(1))
                            print(f"ignoring event: cahnnel pressure: {pressure}")
                            
                        case 0xE:
                            # pitch wheel change
                            lsb = int.from_bytes(midi_file.read(1)) & 0x7f
                            msb = int.from_bytes(midi_file.read(1)) & 0x7f
                            change = msb << 7 + lsb
                            print(f"ignoring event: pitch wheel: {change}")

                        case _: # Default case (catch-all)
                            # Code to execute if no other patterns match
                            raise ValueError("unexpected event type")
                else:
                    match status & 0xF:
                        case 0x0 | 0x7:
                            print("system exclusive event, ignoring due to no implementation")
                            sysex_len = parse_variable_length(midi_file)
                            print("content", midi_file.read(sysex_len))
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
                            match type:
                                case 1 | 2 | 3 | 4 | 5 | 6 | 7:
                                    text = midi_file.read(meta_event_len)
                                    print(f"text data:{text}")
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
                                    ) / 1000000
                                    tick = tempo / divisions
                                case 0x58:
                                    # time signature
                                    num = int.from_bytes(midi_file.read(1))
                                    den = 2 ** int.from_bytes(midi_file.read(1))
                                    clocks = int.from_bytes(midi_file.read(1))
                                    useless = int.from_bytes(midi_file.read(1))
                                case _:
                                    content = midi_file.read(meta_event_len)
                                    print(f"unknown meta event with type: {type} and content: {content}")
                        case _:
                            raise ValueError(f"undefined event: {hex(status)}")
            buffer = ((buffer & 0x00ffffff) << 8) + int.from_bytes(midi_file.read(1))
        else:
            buffer = ((buffer & 0x00ffffff) << 8) + int.from_bytes(midi_file.read(1))
    
    midi_file.close()
    print(f"number of unclosed events: {sum([len(channel.ongoing_events) for channel in midi_channels])}")
    return [evt for channel in midi_channels for evt in channel.closed_events]



lst = parse_midi("Columns_Original.mid")
srted = sorted(lst, key=lambda e: e.timestamp)

with open("Columns_Original.txt", "w") as f:
    for evnt in srted:
        f.write(f".word {int(1000 * evnt.timestamp)}, {evnt.pitch}, {int(evnt.duration * 1000)}, {evnt.instrument}, {evnt.volume}\n")
    print(len(srted))