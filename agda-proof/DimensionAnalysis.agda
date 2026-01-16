{-
================================================================================
  次元解析による「掛け算の順序」の誤解への反証
================================================================================

【反論への回答】
  「5×2 は 5錠×2回 と 2錠×5回 で意味が異なる」という主張に対する反証。

【物理的事実】
  「回数」は無次元量（スカラー）である。
  したがって：
    錠 × 回 = 錠
    回 × 錠 = 錠
  どちらの順序でも結果の次元は「錠」になる。

【結論】
  次元解析の観点からも、掛け算の順序は問題にならない。

================================================================================
-}

module source where

-- ============================================================================
-- 自然数の定義
-- ============================================================================
data ℕ : Set where
  zero : ℕ
  suc  : ℕ → ℕ

one : ℕ
one = suc zero

two : ℕ
two = suc one

five : ℕ
five = suc (suc (suc two))

ten : ℕ
ten = suc (suc (suc (suc (suc five))))

-- ============================================================================
-- 等価性の定義
-- ============================================================================
data _≡_ {A : Set} : A → A → Set where
  refl : {x : A} → x ≡ x

infix 4 _≡_

sym : {A : Set} {x y : A} → x ≡ y → y ≡ x
sym refl = refl

trans : {A : Set} {x y z : A} → x ≡ y → y ≡ z → x ≡ z
trans refl refl = refl

cong : {A B : Set} {x y : A} → (f : A → B) → x ≡ y → f x ≡ f y
cong f refl = refl

-- ============================================================================
-- 加法と乗法の定義
-- ============================================================================
_+_ : ℕ → ℕ → ℕ
zero    + n = n
(suc m) + n = suc (m + n)

_*_ : ℕ → ℕ → ℕ
zero    * n = zero
(suc m) * n = n + (m * n)

infixl 6 _+_
infixl 7 _*_

-- ============================================================================
-- 次元の定義
-- ============================================================================
{-
【物理学的事実】
  - 「錠」は次元を持つ量（薬の個数）
  - 「回」は無次元量（スカラー、単なる回数）

【次元計算の規則】
  無次元 × 有次元 = 有次元
  有次元 × 無次元 = 有次元
  つまり：回 × 錠 = 錠、錠 × 回 = 錠
-}

data Dimension : Set where
  Dimensionless : Dimension  -- 無次元（回数など）
  Tablet        : Dimension  -- 錠（薬の個数）

-- ============================================================================
-- 次元の掛け算規則
-- ============================================================================
{-
【規則】
  無次元 × d = d
  d × 無次元 = d
  これにより、回数（無次元）と錠（有次元）の掛け算は
  どちらの順序でも「錠」になる。
-}

_dim*_ : Dimension → Dimension → Dimension
Dimensionless dim* d = d              -- 無次元 × d = d
d dim* Dimensionless = d              -- d × 無次元 = d
Tablet dim* Tablet = Tablet           -- 錠 × 錠 = 錠（仮定、実際は錠²だが簡略化）

infixl 7 _dim*_

-- ============================================================================
-- 【証明】回 × 錠 = 錠 × 回 = 錠
-- ============================================================================

-- 回（無次元）× 錠 = 錠
times-mul-tablet : Dimensionless dim* Tablet ≡ Tablet
times-mul-tablet = refl

-- 錠 × 回（無次元）= 錠
tablet-mul-times : Tablet dim* Dimensionless ≡ Tablet
tablet-mul-times = refl

-- 【核心】どちらの順序でも同じ次元になる
dimension-commutes : Dimensionless dim* Tablet ≡ Tablet dim* Dimensionless
dimension-commutes = refl

-- ============================================================================
-- 次元付き数量の定義
-- ============================================================================

data Quantity : Dimension → Set where
  qty : (n : ℕ) → (d : Dimension) → Quantity d

value : {d : Dimension} → Quantity d → ℕ
value (qty n _) = n

-- ============================================================================
-- 具体例の定義
-- ============================================================================

-- 5錠（次元: Tablet）
five-tablets : Quantity Tablet
five-tablets = qty five Tablet

-- 2回（次元: Dimensionless = 無次元）
two-times : Quantity Dimensionless
two-times = qty two Dimensionless

-- 2錠（次元: Tablet）
two-tablets : Quantity Tablet
two-tablets = qty two Tablet

-- 5回（次元: Dimensionless = 無次元）
five-times : Quantity Dimensionless
five-times = qty five Dimensionless

-- ============================================================================
-- 次元付き掛け算の定義
-- ============================================================================
{-
【定義】
  次元付き数量の掛け算は：
  - 数値部分は通常の掛け算
  - 次元部分は次元の掛け算規則に従う
-}

-- 汎用的な次元付き掛け算
_×ᵈ_ : {d₁ d₂ : Dimension} → Quantity d₁ → Quantity d₂ → Quantity (d₁ dim* d₂)
(qty n₁ d₁) ×ᵈ (qty n₂ d₂) = qty (n₁ * n₂) (d₁ dim* d₂)

infixl 7 _×ᵈ_

-- ============================================================================
-- 【核心の証明】
-- ============================================================================

{-
【証明1】5錠 × 2回 の結果は「錠」次元
-}
result-5t-2x : Quantity (Tablet dim* Dimensionless)
result-5t-2x = five-tablets ×ᵈ two-times

-- 結果の次元は Tablet
result-5t-2x-dimension : Tablet dim* Dimensionless ≡ Tablet
result-5t-2x-dimension = refl

{-
【証明2】2回 × 5錠 の結果も「錠」次元
-}
result-2x-5t : Quantity (Dimensionless dim* Tablet)
result-2x-5t = two-times ×ᵈ five-tablets

-- 結果の次元は Tablet
result-2x-5t-dimension : Dimensionless dim* Tablet ≡ Tablet
result-2x-5t-dimension = refl

{-
【証明3】両方の結果は同じ次元（Tablet）を持つ
-}
same-dimension : (Tablet dim* Dimensionless) ≡ (Dimensionless dim* Tablet)
same-dimension = refl

-- ============================================================================
-- 交換法則の証明（数値部分）
-- ============================================================================

-- 加法の補題
+-identityʳ : (n : ℕ) → n + zero ≡ n
+-identityʳ zero = refl
+-identityʳ (suc n) = cong suc (+-identityʳ n)

+-sucʳ : (m n : ℕ) → m + suc n ≡ suc (m + n)
+-sucʳ zero n = refl
+-sucʳ (suc m) n = cong suc (+-sucʳ m n)

+-comm : (m n : ℕ) → m + n ≡ n + m
+-comm zero n = sym (+-identityʳ n)
+-comm (suc m) n = trans (cong suc (+-comm m n)) (sym (+-sucʳ n m))

+-assoc : (m n p : ℕ) → (m + n) + p ≡ m + (n + p)
+-assoc zero n p = refl
+-assoc (suc m) n p = cong suc (+-assoc m n p)

-- 乗法の補題
*-zeroʳ : (n : ℕ) → n * zero ≡ zero
*-zeroʳ zero = refl
*-zeroʳ (suc n) = *-zeroʳ n

*-sucʳ : (m n : ℕ) → m * suc n ≡ m + m * n
*-sucʳ zero n = refl
*-sucʳ (suc m) n =
  let step1 = cong (λ x → suc n + x) (*-sucʳ m n)
      step3 = cong suc (sym (+-assoc n m (m * n)))
      step4 = cong (λ x → suc (x + m * n)) (+-comm n m)
      step5 = cong suc (+-assoc m n (m * n))
  in trans step1 (trans step3 (trans step4 step5))

-- 掛け算の交換法則
*-comm : (m n : ℕ) → m * n ≡ n * m
*-comm zero n = sym (*-zeroʳ n)
*-comm (suc m) n =
  let ih = *-comm m n
      step1 = cong (λ x → n + x) ih
      step2 = sym (*-sucʳ n m)
  in trans step1 step2

{-
【証明4】数値部分も等しい（5×2 = 2×5 = 10）
-}
values-equal : five * two ≡ two * five
values-equal = *-comm five two

-- ============================================================================
-- 【最終結論】
-- ============================================================================
{-
================================================================================
  【反証完了】

  「5錠×2回」と「2回×5錠」について：

  1. 【次元】どちらも結果は「錠」次元
     - 錠 × 無次元 = 錠
     - 無次元 × 錠 = 錠
     （回数は無次元だから）

  2. 【数値】どちらも結果は 10
     - 5 × 2 = 10
     - 2 × 5 = 10
     （交換法則より）

  3. 【結論】
     次元解析の観点からも、数値計算の観点からも、
     掛け算の順序は結果に影響しない。

     「意味が違う」という主張は、数学的には誤りである。

================================================================================
-}
