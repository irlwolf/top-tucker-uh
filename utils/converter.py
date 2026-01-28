import subprocess
import os

async def convert_to_24bit(input_file, output_format="flac"):
    base = os.path.splitext(input_file)[0]
    output_file = f"{base}_24bit.{output_format}"
    
    # -sample_fmt s32 forces 24-bit depth during encoding
    cmd = [
        'ffmpeg', '-y', '-i', input_file,
        '-sample_fmt', 's32', '-ar', '96000',
        '-c:a', 'flac' if output_format == "flac" else 'alac',
        output_file
    ]
    
    process = await asyncio.create_subprocess_exec(*cmd)
    await process.wait()
    return output_file
