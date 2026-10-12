def primeCheck (n : Nat) : Bool :=
  if n < 2 then false
  else if n = 2 then true
  else if n % 2 = 0 then false
  else
    let rec check (d : Nat) (fuel : Nat) : Bool :=
      match fuel with
      | 0 => true
      | fuel + 1 =>
        if d * d > n then true
        else if n % d = 0 then false
        else check (d + 2) fuel
    check 3 (n / 2)

def isPrime (n : Nat) : Prop := primeCheck n = true

def claim (n : Nat) : Prop :=
  n > 1 →
    (∃ p, p < n * n ∧ n * (n - 1) < p ∧ isPrime p) ∧
    (∃ p, p < n * (n + 1) ∧ n * n < p ∧ isPrime p)

instance : DecidablePred claim := fun _ => by decide
