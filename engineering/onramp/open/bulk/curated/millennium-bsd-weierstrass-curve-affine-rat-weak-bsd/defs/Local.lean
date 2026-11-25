/-
Copyright 2026 The Formal Conjectures Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-/

import Mathlib
import Defs.WikipediaHasseWeil

/-! Ported by hand from `FormalConjectures/Millennium/BSD.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by curator A (F14 hand curation, cross-file class): the file's definition `WeakBSD`, the only one the weak statements use, without `bsdQuotient` and `StrongBSD` (which need the instance `EllipticCurveRank.mordell_weil`, a theorem the registry states without a proof), the line `attribute [local instance] EllipticCurveRank.mordell_weil` (which `WeakBSD` does not use), and the conjectures it states. The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# The Birch and Swinnerton-Dyer (BSD) Conjecture

## References

- [The Clay Institute](https://www.claymath.org/millennium/birch-and-swinnerton-dyer-conjecture/),
  official problem description by Andrew Wiles:
  [claymath.org](https://www.claymath.org/wp-content/uploads/2022/05/birchswin.pdf)
- [BSD1965] B. J. Birch and H. P. F. Swinnerton-Dyer. "Notes on elliptic curves. II."
  Journal fur die reine und angewandte Mathematik 218 (1965), 79-108,
  [doi](https://doi.org/10.1515/crll.1965.218.79)
- [Tate1966] John Tate. "On the conjectures of Birch and Swinnerton-Dyer and a geometric analog."
  Seminaire Bourbaki, Vol. 9, Exp. No. 306 (1966), 415-440,
  [numdam](https://www.numdam.org/item/SB_1964-1966__9__415_0/)
- [Gross2011] Benedict H. Gross. "Lectures on the conjecture of Birch and Swinnerton-Dyer."
  Arithmetic of L-functions, IAS/Park City Math. Ser. 18, AMS (2011), 169-209,
  [math.harvard.edu](https://people.math.harvard.edu/~gross/preprints/lectures-pcmi.pdf)
- [Ang2025] David Kurniadi Angdinata. "L-functions of Dirichlet twists of elliptic curves:
  computations and congruences." PhD thesis, University College London (2025),
  [discovery.ucl.ac.uk](https://discovery.ucl.ac.uk/10223687/1/main-pages.pdf)
- [Ada] Tom Adamczewski. "Autoformalized conjectures",
  [Birch and Swinnerton-Dyer](https://tadamcz.com/autoformalization-results/#/p/wp-birch-and-swinnerton-dyer-conjecture)
- [DD2010] Tim Dokchitser and Vladimir Dokchitser. "On the Birch-Swinnerton-Dyer quotients
  modulo squares." Annals of Mathematics 172 (2010), 567-596, Conjecture 2.1,
  [annals](https://annals.math.princeton.edu/wp-content/uploads/annals-v172-n1-p11-p.pdf)
-/

section

namespace WeierstrassCurve.Affine

open Projective HasseWeil NumberField

namespace NumberField

variable {K : Type*} [Field K] [NumberField K] [DecidableEq K] (E : Affine K)

/-- The **weak Birch and Swinnerton-Dyer conjecture** for a number field `K`: for every elliptic
curve `E` over `K`, the L-series of `E` has a meromorphic continuation whose order at `s = 1` is
`rk E(K)`. Following [DD2010], Conjecture 2.1 (1), the continuation is asserted rather than assumed,
so this implies `HasseWeil.exists_hasMeromorphicContinuation`. [Tate1966], Conjecture (A) and
[Gross2011], Conjecture 2.10 instead take a continuation as given and state only the order, and
[Gross2011] needs one only near `s = 1`. By `HasseWeil.HasMeromorphicContinuation.unique` the order
does not depend on which continuation is taken, so the two readings differ exactly by the
Hasse--Weil conjecture. -/
def WeakBSD : Prop :=
  ∃ L : ℂ → ℂ, HasMeromorphicContinuation E L ∧ meromorphicOrderAt L 1 = Module.finrank ℤ E.Point

end NumberField

end WeierstrassCurve.Affine
