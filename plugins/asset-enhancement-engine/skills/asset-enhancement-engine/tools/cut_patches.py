"""Cut named rectangular patches from images into a folder + a contact sheet.
usage: python -P cut_patches.py <spec.json> <out_dir>   spec: [{"name", "image", "box": [x0, y0, x1, y1]}]"""
import sys, json, os, cv2, numpy as np
spec = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
tiles = []
for s in spec:
    im = cv2.imread(s["image"]); x0, y0, x1, y1 = s["box"]; p = im[y0:y1, x0:x1]
    cv2.imwrite(os.path.join(out, s["name"] + ".png"), p)
    t = cv2.resize(p, (320, 320), interpolation=cv2.INTER_AREA)
    cv2.putText(t, s["name"], (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1); tiles.append(t)
rows = [np.hstack(tiles[i:i + 4] + [np.zeros((320, 320, 3), np.uint8)] * (4 - len(tiles[i:i + 4]))) for i in range(0, len(tiles), 4)]
cv2.imwrite(os.path.join(out, "_contact.png"), np.vstack(rows)); print(len(spec), "patches")
