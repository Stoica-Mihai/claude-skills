# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "opencv-python-headless>=4.9",
#     "numpy>=1.24",
#     "scikit-image>=0.22",
#     "Pillow>=10.0",
# ]
# ///
"""Align two screenshots, gate on similarity, emit a highlighted diff + JSON.

The deterministic half of the compare-screenshots skill: alignment, similarity
scoring, region clustering, and the overlay image. The semantic "what changed"
rundown is left to the caller's vision.

Alignment adapts to the inputs, because the two common cases want opposite
things:

  * Same dimensions (a regression before/after) — the user cares about
    sub-pixel element moves, so we only cancel a whole-frame scroll
    (translation). Warping more than that would re-seat a moved element and
    hide the layout shift the diff exists to catch.

  * Different dimensions (captures at different zoom / aspect / crop — which is
    normal, screenshots are not guaranteed to match) — here a global scale and
    pan are expected, not a bug, so we register the two with a feature-matched
    *similarity* transform (scale + rotation + translation, 4 DOF). That lines
    the shared content up regardless of size. It is deliberately NOT a full
    affine/perspective warp, so it still cannot mask a local element move.

Either way the diff is restricted to the region where both images actually
overlap, so the borders introduced by warping are never counted as changes.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

GRAY_BG = 128


def load(path):
    """Return (bgr, alpha_or_None). Alpha matters: two screenshots can be
    identical in color yet differ only in transparency."""
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        sys.exit(json.dumps({"error": f"could not read image: {path}"}))
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), None
    if img.shape[2] == 4:
        return np.ascontiguousarray(img[:, :, :3]), np.ascontiguousarray(img[:, :, 3])
    return img, None


def composite(bgr, alpha):
    if alpha is None:
        return bgr
    a = (alpha.astype(np.float32) / 255.0)[:, :, None]
    return (bgr.astype(np.float32) * a + GRAY_BG * (1 - a)).astype(np.uint8)


def _validity(src_shape, M, size):
    ones = np.full(src_shape[:2], 255, np.uint8)
    return cv2.warpAffine(ones, M, size, flags=cv2.INTER_NEAREST)


def align(ref_bgr, mov_bgr, mov_alpha):
    """Return (mov_bgr, mov_alpha, valid_mask, method). valid_mask is 255 where
    the warped comparison image actually has content to compare against."""
    h, w = ref_bgr.shape[:2]
    full_valid = np.full((h, w), 255, np.uint8)

    if mov_bgr.shape[:2] == (h, w):
        # Same size: translation-only, so real element moves stay visible.
        g_ref = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        g_mov = cv2.cvtColor(mov_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        try:
            warp = np.eye(2, 3, dtype=np.float32)
            crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-4)
            cv2.findTransformECC(g_ref, g_mov, warp, cv2.MOTION_TRANSLATION, crit, None, 5)
            if abs(warp[0, 2]) > 0.5 or abs(warp[1, 2]) > 0.5:
                flags = cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP
                mb = cv2.warpAffine(mov_bgr, warp, (w, h), flags=flags, borderValue=(GRAY_BG,) * 3)
                ma = (cv2.warpAffine(mov_alpha, warp, (w, h), flags=flags, borderValue=0)
                      if mov_alpha is not None else None)
                valid = cv2.warpAffine(full_valid, warp, (w, h), flags=flags)
                return mb, ma, valid, "translation"
        except cv2.error:
            pass
        return mov_bgr, mov_alpha, full_valid, "resize"

    # Different size: feature-based similarity registration (scale+rot+trans).
    g_ref = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)
    g_mov = cv2.cvtColor(mov_bgr, cv2.COLOR_BGR2GRAY)
    try:
        orb = cv2.ORB_create(5000)
        k1, d1 = orb.detectAndCompute(g_ref, None)
        k2, d2 = orb.detectAndCompute(g_mov, None)
        if d1 is not None and d2 is not None and len(k1) >= 12 and len(k2) >= 12:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = sorted(bf.match(d2, d1), key=lambda m: m.distance)
            good = matches[: max(20, len(matches) * 3 // 4)]
            if len(good) >= 12:
                src = np.float32([k2[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                dst = np.float32([k1[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
                M, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                                         ransacReprojThreshold=5.0)
                if M is not None and inliers is not None and int(inliers.sum()) >= 10:
                    flags = cv2.INTER_LINEAR
                    mb = cv2.warpAffine(mov_bgr, M, (w, h), flags=flags, borderValue=(GRAY_BG,) * 3)
                    ma = (cv2.warpAffine(mov_alpha, M, (w, h), flags=flags, borderValue=0)
                          if mov_alpha is not None else None)
                    valid = _validity(mov_bgr.shape, M, (w, h))
                    return mb, ma, valid, "similarity"
    except cv2.error:
        pass

    # Fallback: plain resize (aspect-stretching) when features won't register.
    # Labelled distinctly so the caller can warn that boxes may be unreliable —
    # a stretch across mismatched aspect ratios distorts content.
    interp = cv2.INTER_AREA
    mb = cv2.resize(mov_bgr, (w, h), interpolation=interp)
    ma = cv2.resize(mov_alpha, (w, h), interpolation=interp) if mov_alpha is not None else None
    return mb, ma, full_valid, "resize-fallback"


def _delta(ref_bgr, mov_bgr, ref_a, mov_a):
    d = cv2.absdiff(cv2.GaussianBlur(ref_bgr, (3, 3), 0),
                    cv2.GaussianBlur(mov_bgr, (3, 3), 0)).max(axis=2)
    if ref_a is not None or mov_a is not None:
        ra = ref_a if ref_a is not None else np.full(d.shape, 255, np.uint8)
        ma = mov_a if mov_a is not None else np.full(d.shape, 255, np.uint8)
        d = np.maximum(d, cv2.absdiff(ra, ma))
    return d


def content_similarity(ref_bgr, mov_bgr, ref_a, mov_a, valid, tolerance):
    """Fraction of the overlapping foreground where the two images agree.

    Plain SSIM is dominated by a shared flat background, so two unrelated
    screens score deceptively high. This looks only at foreground pixels (those
    differing from each image's dominant background colour), inside the region
    where both images overlap, so the number tracks what a viewer sees."""
    def foreground(img):
        binned = (img // 16).reshape(-1, 3)
        vals, counts = np.unique(binned, axis=0, return_counts=True)
        bg = vals[counts.argmax()].astype(np.int16) * 16
        return np.abs(img.astype(np.int16) - bg).max(axis=2) > tolerance

    fg = (foreground(ref_bgr) | foreground(mov_bgr)) & (valid > 0)
    if ref_a is not None:
        fg |= (ref_a < 250) & (valid > 0)
    if mov_a is not None:
        fg |= (mov_a < 250) & (valid > 0)
    area = int(fg.sum())
    if area == 0:
        return 100.0
    delta = _delta(ref_bgr, mov_bgr, ref_a, mov_a)
    match = int(((delta <= tolerance) & fg).sum())
    return round(100 * match / area, 2)


def diff_mask(ref_bgr, mov_bgr, ref_a, mov_a, valid, tolerance, warped):
    # A scale/translation warp never lines up anti-aliased edges perfectly, so
    # it leaves a thin residual along every glyph and border. Shrinking the
    # valid region and raising the threshold for warped inputs keeps that
    # residual out without hiding real (solid, higher-contrast) changes.
    if warped:
        tolerance = tolerance + 18
        valid = cv2.erode(valid, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)))
    delta = _delta(ref_bgr, mov_bgr, ref_a, mov_a)
    mask = (((delta > tolerance) & (valid > 0)).astype(np.uint8)) * 255

    # Structure gating: keep only diffs that sit on real content — text, icons,
    # lines, button edges — and drop diffs in smooth gradient areas. A
    # translucent UI's blurred backdrop is a textureless gradient: it generates
    # boxes both when it genuinely differs and (worse) when a single global
    # alignment can't co-register a differently-framed background. Neither is a
    # UI change. Real changes carry edges and survive; smooth backdrop does not.
    g_ref = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)
    g_mov = cv2.cvtColor(mov_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.bitwise_or(cv2.Canny(g_ref, 50, 150), cv2.Canny(g_mov, 50, 150))
    structure = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)), iterations=2)
    mask = cv2.bitwise_and(mask, structure)

    if warped:
        # Opening erases thin edge-residual lines while leaving solid blocks.
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    return mask


def merge_boxes(boxes, mx, my):
    """Union boxes that sit close to each other, so a row of adjacent glyph
    boxes (a menu bar, a footer line) collapses into one region a human reads
    as a single change instead of a dozen per-letter specks. The horizontal
    reach `mx` is generous (merge words across a line) but the vertical reach
    `my` is tight, so stacked-but-distinct elements (menu bar vs the row below
    it) are NOT chained into one giant blob."""
    rects = [[x - mx, y - my, x + w + mx, y + h + my] for x, y, w, h in boxes]
    changed = True
    while changed:
        changed = False
        out = []
        while rects:
            a = rects.pop()
            grew = True
            while grew:
                grew = False
                keep = []
                for b in rects:
                    if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                        a = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                        grew = changed = True
                    else:
                        keep.append(b)
                rects = keep
            out.append(a)
        rects = out
    merged = []
    for x0, y0, x1, y1 in rects:
        x0, y0 = max(0, x0 + mx), max(0, y0 + my)
        merged.append((x0, y0, max(1, x1 - mx - x0), max(1, y1 - my - y0)))
    merged.sort(key=lambda b: b[2] * b[3], reverse=True)
    return merged


def regions(mask, min_area, mx, my):
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    closed = cv2.dilate(closed, k, iterations=1)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours]
    boxes = [(x, y, w, h) for (x, y, w, h) in boxes if w * h >= min_area]
    return merge_boxes(boxes, mx, my)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("img1", help="reference / 'before' screenshot")
    ap.add_argument("img2", help="comparison / 'after' screenshot")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tolerance", type=int, default=30,
                    help="per-channel intensity delta ignored as noise (0-255, default 30)")
    ap.add_argument("--gate", type=float, default=0.4,
                    help="min content similarity (0-1) to consider the pair comparable (default 0.4)")
    ap.add_argument("--min-area", type=int, default=80,
                    help="min region area in px to report (default 80)")
    ap.add_argument("--max-regions", type=int, default=10,
                    help="max regions to report with crops; the rest are drawn faintly and counted (default 10)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    ref_bgr, ref_a = load(args.img1)
    raw_bgr, raw_a = load(args.img2)
    mov_bgr, mov_a, valid, method = align(ref_bgr, raw_bgr, raw_a)

    ref_disp = composite(ref_bgr, ref_a)
    mov_disp = composite(mov_bgr, mov_a)
    g_ref = cv2.cvtColor(ref_disp, cv2.COLOR_BGR2GRAY)
    g_mov = cv2.cvtColor(mov_disp, cv2.COLOR_BGR2GRAY)
    ssim_score = round(float(ssim(g_ref, g_mov)), 4)
    similarity_pct = content_similarity(ref_bgr, mov_bgr, ref_a, mov_a, valid, args.tolerance)

    mask = diff_mask(ref_bgr, mov_bgr, ref_a, mov_a, valid, args.tolerance,
                     warped=method in ("similarity", "translation", "resize-fallback"))
    total_px = mask.shape[0] * mask.shape[1]
    changed_pct = round(100 * int((mask > 0).sum()) / total_px, 2)
    mx = max(30, int(0.025 * ref_bgr.shape[1]))
    my = max(6, int(0.012 * ref_bgr.shape[0]))
    boxes = regions(mask, args.min_area, mx, my)
    comparable = bool(similarity_pct >= args.gate * 100)

    result = {
        "similarity_percent": similarity_pct,
        "ssim": ssim_score,
        "alignment": method,
        "gate_threshold": args.gate,
        "comparable": comparable,
        "changed_pixel_percent": changed_pct,
        "reference_dims": [int(ref_bgr.shape[1]), int(ref_bgr.shape[0])],
        "comparison_dims": [int(raw_bgr.shape[1]), int(raw_bgr.shape[0])],
        "has_alpha": bool(ref_a is not None or raw_a is not None),
        "regions": [],
        "overlay_path": None,
    }
    if method == "resize-fallback":
        result["alignment_note"] = ("feature registration failed (too few stable features, "
                                     "common on thin bars or low-detail images); fell back to a "
                                     "stretch-resize across mismatched dimensions, so boxes may be "
                                     "unreliable — lean on the crops and your own read")

    if not comparable:
        result["message"] = (
            f"The two images are too dissimilar to diff meaningfully — content "
            f"similarity is only {similarity_pct}% (below the {int(args.gate*100)}% "
            "floor), so they share little common foreground. They look like "
            "different screens rather than a before/after of the same one. "
            f"(Raw SSIM {ssim_score} can read higher but is inflated by matching background.)")
        print(json.dumps(result, indent=2))
        return

    # Per-region confidence that the box is a real change, not alignment
    # residual. Driven by whether the edge STRUCTURE differs (content added or
    # removed — unambiguous) versus only colour shifting under an alignment we
    # cannot fully trust (likely residual). Colour the box accordingly.
    reliable = method in ("resize", "translation")
    CONF_COLOR = {"high": (0, 0, 255), "medium": (0, 165, 255), "low": (170, 170, 170)}

    def confidence(box):
        x, y, w, h = box
        er = cv2.Canny(g_ref[y:y + h, x:x + w], 50, 150) > 0
        em = cv2.Canny(g_mov[y:y + h, x:x + w], 50, 150) > 0
        denom = int(er.sum()) + int(em.sum())
        if denom == 0:
            struct = 1.0  # changed area with no edges either side — trust the delta
        else:
            k = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            erd = cv2.dilate(er.astype(np.uint8), k) > 0
            emd = cv2.dilate(em.astype(np.uint8), k) > 0
            unmatched = int((er & ~emd).sum()) + int((em & ~erd).sum())
            struct = unmatched / denom  # edges with no counterpart nearby = real content change
        if reliable or struct >= 0.35:
            label = "high"
        elif struct >= 0.15:
            label = "medium"
        else:
            label = "low"
        return label, round(struct, 3)

    primary = boxes[: args.max_regions]
    tail = boxes[args.max_regions:]
    overlay = ref_disp.copy()
    for (x, y, w, h) in tail:
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (170, 170, 170), 1)
    conf_counts = {"high": 0, "medium": 0, "low": 0}
    for i, (x, y, w, h) in enumerate(primary, 1):
        label, struct = confidence((x, y, w, h))
        conf_counts[label] += 1
        color = CONF_COLOR[label]
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 3)
        cv2.putText(overlay, str(i), (x + 4, y + 24), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, color, 2, cv2.LINE_AA)
        pad = 8
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(ref_bgr.shape[1], x + w + pad), min(ref_bgr.shape[0], y + h + pad)
        cb = os.path.join(args.out_dir, f"region{i}_before.png")
        ca = os.path.join(args.out_dir, f"region{i}_after.png")
        cv2.imwrite(cb, ref_disp[y0:y1, x0:x1])
        cv2.imwrite(ca, mov_disp[y0:y1, x0:x1])
        result["regions"].append({
            "id": i, "box_xywh": [int(x), int(y), int(w), int(h)],
            "area_px": int(w * h), "confidence": label, "edge_change": struct,
            "crop_before": cb, "crop_after": ca,
        })
    result["confidence_counts"] = conf_counts

    overlay_path = os.path.join(args.out_dir, "diff_overlay.png")
    cv2.imwrite(overlay_path, overlay)
    result["overlay_path"] = overlay_path
    result["minor_regions_collapsed"] = len(tail)
    if not boxes:
        result["message"] = "No changes above tolerance — images are visually identical."
    else:
        msg = (f"{len(primary)} primary changed region(s) reported (ranked by size). "
               "Boxes are coloured by confidence that the change is real: red=high "
               "(content edges differ), amber=medium, gray=low (likely alignment "
               "residual — verify against the crop).")
        if tail:
            msg += (f" {len(tail)} smaller region(s) collapsed (drawn faintly, no crops) — "
                    "usually peripheral reflow or background.")
        result["message"] = msg
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
