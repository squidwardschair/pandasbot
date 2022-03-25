from typing import List
from PIL import Image, ImageDraw, ImageOps, ImageSequence, ImageFont
import asyncio
from pathlib import Path
from io import BytesIO
import functools


def make_dumpy(avatar):
    avatarimage = Image.open(BytesIO(avatar)).convert("RGBA")
    resizedavatar = avatarimage.resize((148, 148))
    bigsize = (resizedavatar.size[0] * 3, resizedavatar.size[1] * 3)
    mask = Image.new('L', bigsize, 0)
    draw1 = ImageDraw.Draw(mask)
    draw1.ellipse((0, 0)+bigsize, fill=255)
    mask = mask.resize(resizedavatar.size, Image.ANTIALIAS)
    resizedavatar.putalpha(mask)
    output = ImageOps.fit(resizedavatar, mask.size, centering=(0.5, 0.5))
    output.putalpha(mask)
    coordinatelist = [(176, 246), (176, 119), (272, 79), (295, 150), (142, 210), (168, 85), (261, 71), (181, 248), (181, 111), (163, 79), (298, 141), (130, 217), (148, 112), (271, 74), (182, 241),
                      (239, 220), (167, 71), (185, 135), (176, 249), (184, 120), (270, 77), (299, 150), (141, 217), (166, 81), (267, 71), (183, 250), (176, 112), (165, 77), (300, 142), (130, 210), (176, 112)]
    dumpyframes: List[Image.Image] = []
    path = Path(__file__).parent / 'images/dumpy/dumpy.gif'
    im = Image.open(path)
    for frameindex, frame in enumerate(ImageSequence.Iterator(im)):
        img: Image.Image = frame.convert("RGBA")
        img.paste(output, coordinatelist[frameindex], output)
        dumpyframes.append(img)
    img_io = BytesIO()
    print(dumpyframes)
    dumpyframes[0].save(img_io, format='GIF', append_images=dumpyframes[1:],
                        save_all=True, duration=im.info['duration'], loop=3)
    img_io.seek(0)
    return img_io


async def dumpy_get(avatar):
    loop = asyncio.get_running_loop()
    thing = functools.partial(make_dumpy, avatar)
    result = await loop.run_in_executor(None, thing)
    return result
