import subprocess
import time

def start_xvfb(display_port):
    # Start the Xvfb server
    subprocess.Popen(["Xvfb", display_port, "-screen", "0", "1280x720x24"])
    time.sleep(2)


def relay_stream_to_destination(
    destination_server: str, audio_sink: str, display_port: str
) -> subprocess.Popen:
    ffmpeg_command = [
        "ffmpeg",
        "-thread_queue_size",
        "512",
        "-f",
        "x11grab",  # Capture video from the display
        "-i",
        display_port,  # Display input (e.g., :0.0)
        "-thread_queue_size",
        "512",
        "-f",
        "pulse",  # Capture system audio using Pulseaudio
        "-i",
        f"{audio_sink}.monitor",  # Audio source (e.g., "default")
        "-c:v",
        "libx264",  # Video codec
        "-preset",
        "ultrafast",  # Encoding speed (ultrafast for real-time)
        "-b:v",
        "2M",  # Video bitrate
        "-c:a",
        "aac",  # Audio codec (AAC)
        "-b:a",
        "128k",  # Audio bitrate
        "-probesize",
        "32M",  # Increase probing size to 32MB
        "-analyzeduration",
        "100M",
        "-r",
        "24",
        "-s",
        "1280x720",
        "-f",
        "flv",  # Output format for RTMP streaming
        destination_server,  # YouTube RTMP stream URL
    ]

    # Run the FFmpeg command to stream the video
    return subprocess.Popen(ffmpeg_command)


# Function to run pactl command and return the output
def run_pactl_command(command):
    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    return result.stdout


# Function to check if virtual_sink1 exists
def check_virtual_sink_exists(sink_name="virtual_sink1"):
    output = run_pactl_command(["pactl", "list", "sinks"])
    return sink_name in output


# Function to create virtual sink if not exists
def create_virtual_sink(sink_name="virtual_sink1"):
    if not check_virtual_sink_exists(sink_name):
        run_pactl_command(
            ["pactl", "load-module", "module-null-sink", f"sink_name={sink_name}"]
        )
