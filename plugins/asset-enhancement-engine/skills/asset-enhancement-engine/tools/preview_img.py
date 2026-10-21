"""Downscaled preview of an image (reads untrusted files as data only). usage: python -I preview_img.py <in> <out> [max_px]"""
import sys, cv2
im = cv2.imread(sys.argv[1]); m = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
s = m / max(im.shape[:2]); cv2.imwrite(sys.argv[2], cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)); print(im.shape)
