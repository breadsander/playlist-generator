#!/usr/bin/env python3

import argparse
import subprocess
import time
import json
import sys
import datetime
from pathlib import Path

DEFAULT_SLEEP_BACKOFF = 4

class InvalidAudioFileError(Exception):
    pass

class PlaylistGenerator(object):
    class PlaylistEntry(object):
        def __init__(self, artist, track):
            self.artist = artist
            self.track = track
            self.time = sys.maxsize

        def key(self):
            return self.artist + ' - ' + self.track

        def string(self):
            return self.key + '@' + self.time

        def update_time(self, time):
            if self.time > time:
                self.time = time

        def dump(self):
            return '{0} | {1}'.format(str(datetime.timedelta(seconds=self.time)), self.key())

    def __init__(self, input_file, granularity, staging_dir=None):
        self.input_file = Path(input_file)
        self.granularity = granularity
        self.parent_dir = None
        self.staging_dir = staging_dir
        self.playlist_file = None
        self.entries = {}

    def initialize(self):
        audio_extensions = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}
        if self.input_file.suffix.lower() not in audio_extensions:
            raise InvalidAudioFileError

        self.parent_dir = self.input_file.parent

        self.playlist_file = self.parent_dir / Path(self.input_file.stem + '_playlist.txt')

        self.staging_dir = self.parent_dir / Path(self.input_file.stem + '_staging')
        self.staging_dir.mkdir()

        ffmpeg_cmd = ['ffmpeg', '-i']
        ffmpeg_cmd += [self.input_file.as_posix()]
        ffmpeg_cmd += ['-f', 'segment', '-segment_time', str(self.granularity)]
        ffmpeg_cmd += ['-c', 'copy']
        ffmpeg_cmd += [self.staging_dir.as_posix() + '/segment_%03d.mp3']
        subprocess.run(ffmpeg_cmd)

        self.num_segments = sum(1 for _ in self.staging_dir.iterdir())

    def generate(self):
        i = 1
        for f in self.staging_dir.iterdir():
            track_time = int(f.stem.split('_')[1]) * self.granularity
            sleep_backoff = DEFAULT_SLEEP_BACKOFF
            songrec_cmd  = ['songrec', 'audio-file-to-recognized-song', f.as_posix()]

            current_time = str(datetime.timedelta(seconds=track_time))
            print('Analyzing segment {0}/{1}'.format(i, self.num_segments))
            while True:
                time.sleep(sleep_backoff)
                result = subprocess.run(songrec_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    sleep_backoff = sleep_backoff * 2
                    print('Failed to analyze {0}, sleeping {1} seconds'.format(f.as_posix(), sleep_backoff))
                    continue
                else:
                    break

            try:
                songrec_json = json.loads(result.stdout)
                artist = songrec_json['track']['subtitle']
                track = songrec_json['track']['title']
                entry = self.PlaylistEntry(artist, track)

                if entry.key() in self.entries:
                    existing = self.entries[entry.key()]
                    existing.update_time(track_time)
                else:
                    entry.update_time(track_time)
                    self.entries[entry.key()] = entry
            except json.JSONDecodeError as e:
                # print(f"Error decoding JSON: {e}")
                pass
            except KeyError as e:
                #print(f"Key not found: {e}")
                #print(json.dumps(songrec_json))
                pass

            i = i + 1

    def dump_entries(self):
        f = self.playlist_file.open('w')
        sorted_entries = dict(sorted(self.entries.items(), key=lambda item: item[1].time))
        for entry in sorted_entries.values():
            entry_str = entry.dump()
            f.write(entry_str + '\n')
        f.close()

    def cleanup(self):
        if self.staging_dir.exists() and self.staging_dir.is_dir():
            for f in self.staging_dir.iterdir():
                if f.is_file():  # Check if it's a file
                    f.unlink()  # Delete the file

            self.staging_dir.rmdir()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-file', '-i', type=str, required=True)
    parser.add_argument('--granularity', '-g', type=int, default=30)
    parser.add_argument('--staging-dir', '-s', type=str)
    args = parser.parse_args()

    if args.staging_dir is not None:
        try:
            PLG = PlaylistGenerator(args.input_file, args.granularity, Path(args.staging_dir))
            PLG.playlist_file = Path('test_playlist.txt')
            PLG.generate()
        except Exception as e:
            pass
        finally:
            PLG.dump_entries()
            exit()

    try:
        PLG = PlaylistGenerator(args.input_file, args.granularity)
        PLG.initialize()
        PLG.generate()
    except Exception as e:
        print(e)
        pass
    finally:
        PLG.dump_entries()
        PLG.cleanup()
        pass

if __name__ == "__main__":
    main()
