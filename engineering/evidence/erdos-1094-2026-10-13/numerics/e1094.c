/* Numerics for Erdos 1094 nodes. Exact integer arithmetic; divisibility of C(n,k) by a prime p
 * decided by Lucas/Kummer: p does NOT divide C(n,k) iff every base-p digit of k is <= the
 * corresponding digit of n. For p > k this reduces to: p | C(n,k) iff n mod p < k.
 *
 * Modes:
 *   good  KMIN KMAX E   : all (n,k) with 2k <= n < k^E (E = 2 or 3) and no prime p <= k dividing
 *                         C(n,k)  (i.e. minFac C(n,k) > k).  Prints "G n k".  Per-k summary "S k count".
 *   hi    KMIN KMAX NMAX: all (n,k) with k^2 <= n < min(NMAX, k!+k) and no prime p <= n/k dividing
 *                         C(n,k) (i.e. minFac C(n,k) > n/k).  Prints "H n k".
 *   resid KMIN KMAX     : all (n,k) with 2k <= n < k^2 and no prime p <= k with n%p < k%p.
 *                         Prints "R n k".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef unsigned long long u64;

static int *primes; static int np;
static void sieve(int lim){
  char *c = calloc(lim+1,1); primes = malloc(sizeof(int)*(lim/2+10)); np=0;
  for(int i=2;i<=lim;i++){ if(!c[i]){ primes[np++]=i; for(long long j=(long long)i*i;j<=lim;j+=i) c[j]=1; } }
  free(c);
}
/* 1 if p does not divide C(n,k) (k digits dominated by n digits) */
static inline int dom(u64 n,u64 k,u64 p){ while(k){ if(k%p > n%p) return 0; k/=p; n/=p; } return 1; }

int main(int argc,char**argv){
  if(argc<4){fprintf(stderr,"usage\n");return 1;}
  const char*mode=argv[1]; u64 kmin=strtoull(argv[2],0,10), kmax=strtoull(argv[3],0,10);
  if(!strcmp(mode,"good")){
    int E=atoi(argv[4]); sieve((int)kmax+1);
    for(u64 k=kmin;k<=kmax;k++){
      u64 lim = (E==2)? k*k : k*k*k; u64 cnt=0;
      u64 x=k; while(x<2*k) x=(x+1)|k;          /* supersets of k's bits: base-2 domination */
      for(; x<lim; x=(x+1)|k){
        int ok=1;
        for(int i=1;i<np && (u64)primes[i]<=k;i++){ if(!dom(x,k,primes[i])){ok=0;break;} }
        if(ok){ printf("G %llu %llu\n",x,k); cnt++; }
      }
      if(k<2*k && 2*k<lim && 0) {}
      fprintf(stderr,"S %llu %llu\n",k,cnt);
    }
  } else if(!strcmp(mode,"hi")){
    u64 nmax=strtoull(argv[4],0,10); sieve((int)(nmax/ (kmin?kmin:1))+2);
    for(u64 k=kmin;k<=kmax;k++){
      u64 f=1; int big=0; for(u64 i=2;i<=k;i++){ if(f> (u64)4e18/i){big=1;break;} f*=i; }
      u64 lim = nmax; if(!big && f+k < lim) lim=f+k;
      for(u64 n=k*k; n<lim; n++){
        u64 B=n/k; int ex=1;
        for(int i=0;i<np && (u64)primes[i]<=B;i++){
          u64 p=primes[i];
          if(p<=k){ if(!dom(n,k,p)){ex=0;break;} }
          else { if(n%p < k){ex=0;break;} }
        }
        if(ex) printf("H %llu %llu\n",n,k);
      }
      fprintf(stderr,"S %llu lim %llu\n",k,lim);
    }
  } else if(!strcmp(mode,"resid")){
    sieve((int)kmax+1);
    for(u64 k=kmin;k<=kmax;k++){
      for(u64 n=2*k;n<k*k;n++){
        int found=0;
        for(int i=0;i<np && (u64)primes[i]<=k;i++){ u64 p=primes[i]; if(n%p < k%p){found=1;break;} }
        if(!found) printf("R %llu %llu\n",n,k);
      }
    }
  }
  return 0;
}
