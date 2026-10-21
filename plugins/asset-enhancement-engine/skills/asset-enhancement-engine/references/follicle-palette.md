# Follicle palette and map (trial E6; person's idea, 2026-10-17)

Person: "when you're building the root (follicle) map/palette, why not make it define hair color and have the color
of those hairs on the palette directly modifiable?" Decision: yes.

## The palette (case file `follicle_palette.json`)
A short list of HAIR TYPES. Each entry is directly editable and fully defines the hairs grown from its follicles:
- kind: guard | awn | down | furnishing | tactile (whiskers, brow, cheek, carpal hairs are separate structures)
- length (mm, with spread), shaft diameter (micrometres, root -> tip taper), lift at the root and lie toward the tip
- curl / crimp, clumping into locks (strength, lock size)
- density per cm2 (real values by region come from the research file cat-hair-streams.md)
- COLOUR ALONG THE SHAFT: root -> band(s) -> tip, so agouti banding, tipping and point colour are hair properties
Example entries for cat1: white guard, lilac guard (markings), white undercoat, ear furnishing, whisker.

## The map (on the skin)
Per skin point: which palette types grow there and in what mix (weights), plus the growth direction from the hair
streams (hair_field.py). Markings are the places where pigmented types grow - a stripe is a band of lilac-guard
follicles, not paint on the skin under white fur.

## Editing
Changing an entry (e.g. the lilac guard colour, or the cheek guard length) changes every hair of that type at the
next groom - no repainting, no re-mapping. Skin pigment (nose leather, paw pads, ear skin) is a separate skin
property in the same spirit: material colour of a structure, never a drawn shape.
