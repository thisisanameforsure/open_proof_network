  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h693 : n ≤ 693
  · exact blk 1361 681 693 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h693
  by_cases h703 : n ≤ 703
  · exact blk 1381 694 703 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h703
  by_cases h712 : n ≤ 712
  · exact blk 1399 704 712 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h712
  by_cases h724 : n ≤ 724
  · exact blk 1423 713 724 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h724
  by_cases h736 : n ≤ 736
  · exact blk 1447 725 736 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h736
  by_cases h749 : n ≤ 749
  · exact blk 1471 737 749 27 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h749
  by_cases h763 : n ≤ 763
  · exact blk 1499 750 763 27 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h763
  by_cases h775 : n ≤ 775
  · exact blk 1523 764 775 27 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h775
  by_cases h788 : n ≤ 788
  · exact blk 1549 776 788 27 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h788
  by_cases h799 : n ≤ 799
  · exact blk 1571 789 799 27 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h799
  by_cases h812 : n ≤ 812
  · exact blk 1597 800 812 27 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h812
  by_cases h824 : n ≤ 824
  · exact blk 1621 813 824 27 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h824
  by_cases h832 : n ≤ 832
  · exact blk 1637 825 832 27 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h832
  by_cases h845 : n ≤ 845
  · exact blk 1663 833 845 27 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h845
  by_cases h849 : n ≤ 849
  · exact blk 1669 846 849 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h849
  by_cases h864 : n ≤ 864
  · exact blk 1699 850 864 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h864
  by_cases h876 : n ≤ 876
  · exact blk 1723 865 876 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h876
  by_cases h891 : n ≤ 891
  · exact blk 1753 877 891 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h891
  by_cases h906 : n ≤ 906
  · exact blk 1783 892 906 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h906
  by_cases h920 : n ≤ 920
  · exact blk 1811 907 920 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h920
  by_cases h930 : n ≤ 930
  · exact blk 1831 921 930 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h930
  by_cases h945 : n ≤ 945
  · exact blk 1861 931 945 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h945
  by_cases h959 : n ≤ 959
  · exact blk 1889 946 959 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h959
  by_cases h971 : n ≤ 971
  · exact blk 1913 960 971 29 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h971
  by_cases h982 : n ≤ 982
  · exact blk 1933 972 982 31 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h982
  by_cases h991 : n ≤ 991
  · exact blk 1951 983 991 31 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h991
  by_cases h1005 : n ≤ 1005
  · exact blk 1979 992 1005 31 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1005
  by_cases h1021 : n ≤ 1021
  · exact blk 2011 1006 1021 31 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1021
  by_cases h1035 : n ≤ 1035
  · exact blk 2039 1022 1035 31 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1035
  by_cases h1050 : n ≤ 1050
  · exact blk 2069 1036 1050 31 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1050
  by_cases h1065 : n ≤ 1065
  · exact blk 2099 1051 1065 31 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1065
  by_cases h1081 : n ≤ 1081
  · exact blk 2131 1066 1081 31 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1081
  by_cases h1096 : n ≤ 1096
  · exact blk 2161 1082 1096 31 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1096
  by_cases h1106 : n ≤ 1106
  · exact blk 2179 1097 1106 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1106
  by_cases h1123 : n ≤ 1123
  · exact blk 2213 1107 1123 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1123
  by_cases h1138 : n ≤ 1138
  · exact blk 2243 1124 1138 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1138
  by_cases h1153 : n ≤ 1153
  · exact blk 2273 1139 1153 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1153
  by_cases h1165 : n ≤ 1165
  · exact blk 2297 1154 1165 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1165
  by_cases h1172 : n ≤ 1172
  · exact blk 2311 1166 1172 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1172
  by_cases h1187 : n ≤ 1187
  · exact blk 2341 1173 1187 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1187
  by_cases h1202 : n ≤ 1202
  · exact blk 2371 1188 1202 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1202
  by_cases h1216 : n ≤ 1216
  · exact blk 2399 1203 1216 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1216
  by_cases h1228 : n ≤ 1228
  · exact blk 2423 1217 1228 33 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1228
  by_cases h1241 : n ≤ 1241
  · exact blk 2447 1229 1241 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1241
  by_cases h1256 : n ≤ 1256
  · exact blk 2477 1242 1256 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1256
  by_cases h1269 : n ≤ 1269
  · exact blk 2503 1257 1269 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1269
  by_cases h1287 : n ≤ 1287
  · exact blk 2539 1270 1287 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1287
  by_cases h1296 : n ≤ 1296
  · exact blk 2557 1288 1296 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1296
  by_cases h1314 : n ≤ 1314
  · exact blk 2593 1297 1314 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1314
  by_cases h1328 : n ≤ 1328
  · exact blk 2621 1315 1328 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1328
  by_cases h1346 : n ≤ 1346
  · exact blk 2657 1329 1346 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1346
  by_cases h1364 : n ≤ 1364
  · exact blk 2693 1347 1364 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1364
  by_cases h1382 : n ≤ 1382
  · exact blk 2729 1365 1382 35 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1382
  by_cases h1395 : n ≤ 1395
  · exact blk 2753 1383 1395 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1395
  by_cases h1414 : n ≤ 1414
  · exact blk 2791 1396 1414 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1414
  by_cases h1428 : n ≤ 1428
  · exact blk 2819 1415 1428 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1428
  by_cases h1447 : n ≤ 1447
  · exact blk 2857 1429 1447 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1447
  by_cases h1462 : n ≤ 1462
  · exact blk 2887 1448 1462 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1462
  by_cases h1477 : n ≤ 1477
  · exact blk 2917 1463 1477 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1477
  by_cases h1495 : n ≤ 1495
  · exact blk 2953 1478 1495 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1495
  by_cases h1504 : n ≤ 1504
  · exact blk 2971 1496 1504 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1504
  by_cases h1519 : n ≤ 1519
  · exact blk 3001 1505 1519 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1519
  by_cases h1537 : n ≤ 1537
  · exact blk 3037 1520 1537 37 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1537
  by_cases h1553 : n ≤ 1553
  · exact blk 3067 1538 1553 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1553
  by_cases h1564 : n ≤ 1564
  · exact blk 3089 1554 1564 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1564
  by_cases h1580 : n ≤ 1580
  · exact blk 3121 1565 1580 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1580
  by_cases h1588 : n ≤ 1588
  · exact blk 3137 1581 1588 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1588
  by_cases h1604 : n ≤ 1604
  · exact blk 3169 1589 1604 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1604
  by_cases h1624 : n ≤ 1624
  · exact blk 3209 1605 1624 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1624
  by_cases h1634 : n ≤ 1634
  · exact blk 3229 1625 1634 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1634
  by_cases h1649 : n ≤ 1649
  · exact blk 3259 1635 1649 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1649
  by_cases h1669 : n ≤ 1669
  · exact blk 3299 1650 1669 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1669
  by_cases h1685 : n ≤ 1685
  · exact blk 3331 1670 1685 39 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1685
  by_cases h1706 : n ≤ 1706
  · exact blk 3371 1686 1706 41 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1706
  by_cases h1727 : n ≤ 1727
  · exact blk 3413 1707 1727 41 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1727
  by_cases h1745 : n ≤ 1745
  · exact blk 3449 1728 1745 41 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1745
  by_cases h1766 : n ≤ 1766
  · exact blk 3491 1746 1766 41 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1766
  by_cases h1787 : n ≤ 1787
  · exact blk 3533 1767 1787 41 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1787
  by_cases h1806 : n ≤ 1806
  · exact blk 3571 1788 1806 41 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1806
  by_cases h1827 : n ≤ 1827
  · exact blk 3613 1807 1827 41 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1827
  by_cases h1842 : n ≤ 1842
  · exact blk 3643 1828 1842 41 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1842
  by_cases h1859 : n ≤ 1859
  · exact blk 3677 1843 1859 41 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1859
  by_cases h1881 : n ≤ 1881
  · exact blk 3719 1860 1881 43 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1881
  by_cases h1902 : n ≤ 1902
  · exact blk 3761 1882 1902 43 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1902
  by_cases h1923 : n ≤ 1923
  · exact blk 3803 1903 1923 43 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1923
  by_cases h1945 : n ≤ 1945
  · exact blk 3847 1924 1945 43 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1945
  by_cases h1966 : n ≤ 1966
  · exact blk 3889 1946 1966 43 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1966
  by_cases h1987 : n ≤ 1987
  · exact blk 3931 1967 1987 43 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h1987
  by_cases h2005 : n ≤ 2005
  · exact blk 3967 1988 2005 43 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2005
  by_cases h2025 : n ≤ 2025
  · exact blk 4007 2006 2025 43 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2025
  by_cases h2048 : n ≤ 2048
  · exact blk 4051 2026 2048 45 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2048
  by_cases h2069 : n ≤ 2069
  · exact blk 4093 2049 2069 45 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2069
  by_cases h2092 : n ≤ 2092
  · exact blk 4139 2070 2092 45 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2092
  by_cases h2111 : n ≤ 2111
  · exact blk 4177 2093 2111 45 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2111
  by_cases h2132 : n ≤ 2132
  · exact blk 4219 2112 2132 45 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2132
  by_cases h2153 : n ≤ 2153
  · exact blk 4261 2133 2153 45 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2153
  by_cases h2171 : n ≤ 2171
  · exact blk 4297 2154 2171 45 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2171
  by_cases h2192 : n ≤ 2192
  · exact blk 4339 2172 2192 45 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2192
  by_cases h2209 : n ≤ 2209
  · exact blk 4373 2193 2209 45 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2209
  by_cases h2228 : n ≤ 2228
  · exact blk 4409 2210 2228 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2228
  omega
