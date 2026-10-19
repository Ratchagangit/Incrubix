# Semantic Timeline & Content Anchors Design

## 1. The Core Principle: Edits Belong to Content, Not Clocks

In traditional non-linear video editors and simplistic automated tools, annotations (captions, mutes, bleeps, and sound effects) are stored as absolute presentation timestamps:
$$\text{Annotation} = (\text{timeline\_start} = 42.0\text{s}, \text{timeline\_end} = 44.0\text{s})$$

If a creator subsequent instructs: *"Cut the first 30 seconds"*, a clock-based system leaves the annotation at $42.0\text{s}$, silently shifting it onto completely unrelated spoken words.

**The IncuBrix engine solves this by strictly separating Source Coordinate Space from Timeline Presentation Space.** Every edit belongs to an immutable source media interval $[t_{\text{src\_start}}, t_{\text{src\_end}})$.

```
Source Space (Seconds):
[0s ---------------- 30s ------- 42s === 44s ---------------------- 300s]
                     |           | Caption: "Welcome!" |
                     |           +---------------------+
                     V
Edit: Cut [0.0s, 30.0s)
                     |
                     V
Timeline Space (Seconds):
[0s ---------------------------- 12s === 14s ---------------------- 270s]
                                 | Caption: "Welcome!" |
                                 +---------------------+
```

## 2. Mathematical Coordinate Mapping

### 2.1 Timeline Representation
A `Timeline` is an ordered sequence of $N$ non-overlapping segments $S_0, S_1, \dots, S_{N-1}$:
$$S_i = \left(\text{source\_media\_id}, \tau_{i,\text{start}}, \tau_{i,\text{end}}, v_i\right)$$
where $[\tau_{i,\text{start}}, \tau_{i,\text{end}})$ is a half-open interval in source time, and $v_i \in [0.25, 10.0]$ is the playback speed factor.

The timeline presentation duration $D_i$ of segment $S_i$ is:
$$D_i = \frac{\tau_{i,\text{end}} - \tau_{i,\text{start}}}{v_i}$$
Total timeline duration is $D = \sum_{i=0}^{N-1} D_i$.

### 2.2 Source to Timeline Mapping: $\mathcal{M}_{\text{src}\to\text{tl}}(t_{\text{src}})$
To project any source timestamp $t_{\text{src}}$ onto the active timeline:
1. Initialize presentation accumulator: $T_{\text{accum}} = 0.0$.
2. For each segment $S_i$:
   - If $\tau_{i,\text{start}} \le t_{\text{src}} < \tau_{i,\text{end}}$:
     $$\mathcal{M}(t_{\text{src}}) = T_{\text{accum}} + \frac{t_{\text{src}} - \tau_{i,\text{start}}}{v_i}$$
   - Increment: $T_{\text{accum}} \leftarrow T_{\text{accum}} + D_i$.
3. If $t_{\text{src}}$ is not contained in any active segment $S_i$, $t_{\text{src}}$ was cut. Return $\text{None}$.

### 2.3 Timeline to Source Mapping: $\mathcal{M}_{\text{tl}\to\text{src}}(t_{\text{tl}})$
Given a timeline playhead coordinate $t_{\text{tl}} \in [0, D)$:
1. Find segment $S_k$ such that $\sum_{i=0}^{k-1} D_i \le t_{\text{tl}} < \sum_{i=0}^k D_i$.
2. Compute elapsed time within segment: $\Delta t = t_{\text{tl}} - \sum_{i=0}^{k-1} D_i$.
3. Return source coordinate:
   $$\tau_{\text{src}} = \tau_{k,\text{start}} + (\Delta t \cdot v_k)$$

## 3. Anchor Transformation Rules & Lifecycle

Content anchors (`ContentAnchor`) maintain an active lifecycle status:

| Operation | Anchor Behavior | Lifecycle State | Diagnostic Policy |
| :--- | :--- | :--- | :--- |
| **Cut (Disjoint)** | Preceding cuts shift presentation time forward. Succeeding cuts have zero effect. | `active = True` | None. Anchor correctly follows word position. |
| **Cut (Full removal)** | Segment containing anchor is completely removed. | `active = False` | Warning recorded. Anchor preserved in history for non-destructive restore. |
| **Cut (Partial removal)** | Cut overlaps portion of anchor's spoken range. | `active = True` | Anchor interval trimmed to surviving content; warning issued. |
| **Reorder** | Segments permuted in presentation order. | `active = True` | Anchor automatically renders at new segment index without coordinate changes. |
| **Speed Change** | Segment speed factor multiplied by $v$. | `active = True` | Anchor timeline duration scaled by $1/v$. If duration $< 0.7\text{s}$, minimum readability warning triggered. |
| **Undo / Restore** | Earlier cut reversed or historical state restored. | `active = True` | Anchor content reactivates at original source alignment. |

## 4. Deterministic Canonical Hashing

To ensure 100% reproducible timelines across runs, timeline state is canonically serialized and hashed:
1. Ephemeral IDs, database auto-increment keys, and execution timestamps are excluded.
2. Floating point values are rounded to 6 decimal places ($10^{-6}\text{s}$).
3. Segments are serialized in presentation order.
4. Anchors are sorted deterministically by `(type, source_start_s)`.
5. JSON serialization uses canonical separators `(',', ':')` and sorted keys before computing SHA-256:
   $$\text{timeline\_hash} = \text{SHA-256}\left(\text{JSON}_{\text{canonical}}(\text{Timeline})\right)$$
