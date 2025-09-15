import os
import argparse
import subprocess
import re
import signal
import sys

def get_list_of_cameras():
    # Run the 'lsusb' command
    result = subprocess.run(['lsusb'], capture_output=True, text=True)
    
    # Define the regex pattern to match the DVXplorer Mini device
    pattern = re.compile(r'Bus (\d{3}) Device (\d{3}):.*DVXplorer Mini')
    
    # Find all matches
    devices = pattern.findall(result.stdout)
    
    # Convert matches into a list of dictionaries
    parsed_devices = [{'Bus': int(bus), 'Device': int(device)} for bus, device in devices]
    
    return parsed_devices

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Fenrir eyes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Execute the script with the -s or --stream flag followed by a stream type below:
            1. stdout             # Streams events over STDOUT into your terminal
            2. udp <ip> <port>    # Stream events over UDP (port argument is optional)
            3. aedat3 [path]      # Save events to a file in AEDAT3.1-format
            4. aedat4 [path]      # Save events to a file in AEDAT4-format
            5. csv [path]         # Save events to a file in CSV-format
            6. file <path>        # Replay events from an input file over STDOUT
        
        Example:
            python open_eyes.py -s udp 172.16.223.245
        """
    )
    parser.add_argument('-i', '--invert_cameras', action="store_true", help="Inverts the event streams to be shown from left to right and vice-versa")
    parser.add_argument('-s', '--stream', nargs='+', help="Stream type and parameters (see below)")
    parser.add_argument('-pSize', '--packet-size', type=int, default=10000)
    parser.add_argument('-bSize', '--buffer-size', type=int, default=2048)
    parser.add_argument('-c', '--continuous', action="store_true", help="Run the script indefinitely until manually terminated, returning to terminal prompt")
    return parser.parse_args()

def run_camera_stream(camera, idx, args, port_list):
    stream_type = args.stream[0] if args.stream else None
    default_ip_out = "172.16.223.245"
    port = port_list[idx]
    
    if stream_type == "udp":
        ip_out = args.stream[1] if len(args.stream) > 1 else default_ip_out
        port = int(args.stream[2]) if len(args.stream) > 2 else port
        cmd = f"/opt/aestream/build/src/aestream input inivation {camera['Bus']} {camera['Device']} dvx 0 output udp {ip_out} {port}"
        print(f"Sending events to: {ip_out} on port: {port}")
    elif stream_type == "stdout":
        cmd = f"/opt/aestream/build/src/aestream input inivation {camera['Bus']} {camera['Device']} dvx 0 output stdout"
    elif stream_type == "aedat4":
        file_path = args.stream[1] if len(args.stream) > 1 else ""
        cmd = f"/opt/aestream/build/src/aestream input inivation {camera['Bus']} {camera['Device']} dvx 0 output file {file_path}camera_{idx}.aedat4"
        print(f"Storing events in: {file_path}camera_{idx}.aedat4")
    elif stream_type == "aedat3":
        file_path = args.stream[1] if len(args.stream) > 1 else ""
        cmd = f"/opt/aestream/build/src/aestream input inivation {camera['Bus']} {camera['Device']} dvx 0 output file {file_path}camera_{idx}.aedat3"
        print(f"Storing events in: {file_path}camera_{idx}.aedat3")
    elif stream_type == "csv":
        file_path = args.stream[1] if len(args.stream) > 1 else ""
        cmd = f"/home/ncs/aestream/build/src/cpp/aestream input inivation {camera['Bus']} {camera['Device']} dvx 0 output file {file_path}camera_{idx}.csv"
        print(f"Storing events in: {file_path}camera_{idx}.csv")
    elif stream_type == "file":
        if len(args.stream) < 2:
            raise ValueError("File stream requires an input file path")
        file_path = args.stream[1]
        cmd = f"/opt/aestream/build/src/aestream input file {file_path} output stdout"
    else:
        raise ValueError("Invalid stream type specified")
    
    #NOTE: Redirect stdout and stderr to /dev/null TO SUPPRESS OUTPUT IN TERMINAL FROM AESTREAM SUBPROCESS
    with open(os.devnull, 'w') as devnull:
        process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid, stdout=devnull, stderr=devnull)
    return process

def signal_handler(sig, frame):
    print("\nTerminating camera streams...")
    # Kill any remaining aestream processes
    os.system("pkill -f aestream")
    global processes
    for process in processes:
        # Send SIGTERM to the process group, this will terminate the processes
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    sys.exit(0)

if __name__ == "__main__":
    # Terminate any existing aestream processes
    os.system("pkill -f aestream")
    
    # Ctrl-C termination gracefully
    signal.signal(signal.SIGINT, signal_handler)

    # Get lists of cameras
    list_of_cameras = get_list_of_cameras()
    if list_of_cameras:
        print("DVXplorer Mini devices found:")
        for device in list_of_cameras:
            print(f"Bus {device['Bus']} Device {device['Device']}")
    else:
        print("No DVXplorer Mini devices found.")
        sys.exit(0)

    args = parse_arguments()
    
    # Check if stream argument is provided
    if not args.stream:
        parser = argparse.ArgumentParser(
            description='Fenrir eyes',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
            Execute the script with the -s or --stream flag followed by a stream type below:
                1. stdout             # Streams events over STDOUT into your terminal
                2. udp <ip> <port>    # Stream events over UDP (port argument is optional)
                3. aedat3 [path]      # Save events to a file in AEDAT3.1-format
                4. aedat4 [path]      # Save events to a file in AEDAT4-format
                5. csv [path]         # Save events to a file in CSV-format
                6. file <path>        # Replay events from an input file over STDOUT
            
            Example:
                python open_eyes.py -s udp 172.16.223.245
            """
        )
        parser.print_help()
        sys.exit(1)
    
    # Assign ports
    if args.invert_cameras:
        port_list = [4001, 4002]
    else:
        port_list = [4002, 4001]
    
    # List to store subprocesses for parallelisation
    processes = []

    # Start streams for all cameras in parallel
    for idx, camera in enumerate(list_of_cameras):
        process = run_camera_stream(camera, idx, args, port_list)
        processes.append(process)

    # If not in continuous mode, wait for processes and show termination message
    if not args.continuous:
        print("Terminate stream with ctrl+c")
        try:
            for process in processes:
                process.wait()
        except KeyboardInterrupt:
            signal_handler(None, None)
    else:
        print("Terminate stream by executing close_eyes.py or killing the aestream subprocess")