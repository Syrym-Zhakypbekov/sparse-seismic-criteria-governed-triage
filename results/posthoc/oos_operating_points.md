# Out-of-sample operating points (post hoc)

## A. Common constraints (chosen on development)

| constraint | test | families meeting both constraints out of sample (fewest unassociated alerts first) |
|---|---|---|
| dism<=3%, esc<=30% | extended IU.MAKZ | P1t 723/1000 alerts, dism 1.0%, esc 0% |
| dism<=3%, esc<=30% | extended II.KURK | P1t 806/1000 alerts, dism 1.8%, esc 0% |
| dism<=3%, esc<=30% | 2024 IU.MAKZ | P1t 795/1000 alerts, dism 0.7%, esc 0% |
| dism<=3%, esc<=30% | 2024 II.KURK | P1t 848/1000 alerts, dism 0.6%, esc 0% |
| dism<=3%, esc<=30% | KZ network | CG-D 355/1000 alerts, dism 2.4%, esc 29%; P1t 761/1000 alerts, dism 0.4%, esc 0% |
| dism<=3%, esc<=40% | extended IU.MAKZ | P1t 723/1000 alerts, dism 1.0%, esc 0% |
| dism<=3%, esc<=40% | extended II.KURK | P1t 806/1000 alerts, dism 1.8%, esc 0% |
| dism<=3%, esc<=40% | 2024 IU.MAKZ | P3 423/1000 alerts, dism 0.7%, esc 38%; P1t 795/1000 alerts, dism 0.7%, esc 0% |
| dism<=3%, esc<=40% | 2024 II.KURK | P3 472/1000 alerts, dism 0.6%, esc 40%; P1t 848/1000 alerts, dism 0.6%, esc 0% |
| dism<=3%, esc<=40% | KZ network | P1t 761/1000 alerts, dism 0.4%, esc 0% |
| dism<=3%, esc<=50% | extended IU.MAKZ | P1t 723/1000 alerts, dism 1.0%, esc 0% |
| dism<=3%, esc<=50% | extended II.KURK | P1t 806/1000 alerts, dism 1.8%, esc 0% |
| dism<=3%, esc<=50% | 2024 IU.MAKZ | P1t 795/1000 alerts, dism 0.7%, esc 0% |
| dism<=3%, esc<=50% | 2024 II.KURK | P1t 848/1000 alerts, dism 0.6%, esc 0% |
| dism<=3%, esc<=50% | KZ network | P1t 761/1000 alerts, dism 0.4%, esc 0% |
| dism<=5%, esc<=30% | extended IU.MAKZ | P1t 668/1000 alerts, dism 2.0%, esc 0% |
| dism<=5%, esc<=30% | extended II.KURK | P1t 756/1000 alerts, dism 3.9%, esc 0% |
| dism<=5%, esc<=30% | 2024 IU.MAKZ | P1t 756/1000 alerts, dism 1.1%, esc 0% |
| dism<=5%, esc<=30% | 2024 II.KURK | P1t 822/1000 alerts, dism 2.1%, esc 0% |
| dism<=5%, esc<=30% | KZ network | P1t 706/1000 alerts, dism 1.1%, esc 0% |
| dism<=5%, esc<=40% | extended IU.MAKZ | P1t 668/1000 alerts, dism 2.0%, esc 0% |
| dism<=5%, esc<=40% | extended II.KURK | P1t 756/1000 alerts, dism 3.9%, esc 0% |
| dism<=5%, esc<=40% | 2024 IU.MAKZ | P1t 756/1000 alerts, dism 1.1%, esc 0% |
| dism<=5%, esc<=40% | 2024 II.KURK | P1t 822/1000 alerts, dism 2.1%, esc 0% |
| dism<=5%, esc<=40% | KZ network | P1t 706/1000 alerts, dism 1.1%, esc 0% |
| dism<=5%, esc<=50% | extended IU.MAKZ | P1t 668/1000 alerts, dism 2.0%, esc 0% |
| dism<=5%, esc<=50% | extended II.KURK | P1t 756/1000 alerts, dism 3.9%, esc 0% |
| dism<=5%, esc<=50% | 2024 IU.MAKZ | P1t 756/1000 alerts, dism 1.1%, esc 0% |
| dism<=5%, esc<=50% | 2024 II.KURK | P1t 822/1000 alerts, dism 2.1%, esc 0% |
| dism<=5%, esc<=50% | KZ network | CG-D 109/1000 alerts, dism 4.7%, esc 50%; P1t 706/1000 alerts, dism 1.1%, esc 0% |

## B. Relative costs (chosen on development)

| r_missed, r_escalation | test | lowest out-of-sample cost per episode (top 3) |
|---|---|---|
| 20, 0.1 | extended IU.MAKZ | P3 0.110; P2 0.110; CG(c=0.5) 0.110 |
| 20, 0.1 | extended II.KURK | P3 0.123; P2 0.123; CG(c=0.5) 0.128 |
| 20, 0.1 | 2024 IU.MAKZ | P3 0.111; P2 0.111; CG-D 0.111 |
| 20, 0.1 | 2024 II.KURK | P3 0.114; P2 0.114; CG-D 0.114 |
| 20, 0.1 | KZ network | CG-D 0.110; P3 0.111; P2 0.111 |
| 20, 0.25 | extended IU.MAKZ | CG-D 0.240; CG(c=0.5) 0.241; CG(c=1) 0.244 |
| 20, 0.25 | extended II.KURK | CG(c=0.5) 0.263; CG-D 0.264; P3 0.267 |
| 20, 0.25 | 2024 IU.MAKZ | CG(c=1) 0.239; CG-D 0.242; CG(c=0.5) 0.244 |
| 20, 0.25 | 2024 II.KURK | CG-D 0.253; CG(c=0.5) 0.253; P3 0.257 |
| 20, 0.25 | KZ network | CG-D 0.242; CG(c=1) 0.244; CG(c=0.5) 0.245 |
| 20, 0.5 | extended IU.MAKZ | P3 0.464; P2 0.464; CG(c=1) 0.480 |
| 20, 0.5 | extended II.KURK | P3 0.493; P2 0.493; CG(c=1) 0.708 |
| 20, 0.5 | 2024 IU.MAKZ | CG(c=0.5) 0.421; CG(c=1) 0.429; CG-D 0.433 |
| 20, 0.5 | 2024 II.KURK | P3 0.491; P2 0.491; CG(c=0.5) 0.641 |
| 20, 0.5 | KZ network | P3 0.479; P2 0.479; CG(c=0.5) 0.485 |
| 50, 0.1 | extended IU.MAKZ | P3 0.130; P2 0.130; CG(c=0.5) 0.136 |
| 50, 0.1 | extended II.KURK | P3 0.144; P2 0.144; CG(c=0.5) 0.159 |
| 50, 0.1 | 2024 IU.MAKZ | P3 0.123; P2 0.123; CG-D 0.133 |
| 50, 0.1 | 2024 II.KURK | P3 0.125; P2 0.125; CG-D 0.132 |
| 50, 0.1 | KZ network | P3 0.121; P2 0.121; CG-D 0.129 |
| 50, 0.25 | extended IU.MAKZ | P3 0.265; P2 0.265; CG(c=0.5) 0.267 |
| 50, 0.25 | extended II.KURK | P3 0.287; P2 0.287; CG(c=0.5) 0.294 |
| 50, 0.25 | 2024 IU.MAKZ | P3 0.263; P2 0.263; CG-D 0.264 |
| 50, 0.25 | 2024 II.KURK | P3 0.269; P2 0.269; CG-D 0.270 |
| 50, 0.25 | KZ network | CG-D 0.261; P3 0.262; P2 0.262 |
| 50, 0.5 | extended IU.MAKZ | P3 0.484; P2 0.484; CG-D 0.484 |
| 50, 0.5 | extended II.KURK | P3 0.514; P2 0.514; CG(c=0.5) 0.524 |
| 50, 0.5 | 2024 IU.MAKZ | CG(c=1) 0.479; CG-D 0.484; CG(c=0.5) 0.486 |
| 50, 0.5 | 2024 II.KURK | CG-D 0.502; CG(c=0.5) 0.503; P3 0.503 |
| 50, 0.5 | KZ network | CG-D 0.482; CG(c=0.5) 0.487; P3 0.489 |
| 100, 0.1 | extended IU.MAKZ | P3 0.162; P2 0.162; CG(c=0.5) 0.179 |
| 100, 0.1 | extended II.KURK | P3 0.178; P2 0.178; CG(c=0.5) 0.211 |
| 100, 0.1 | 2024 IU.MAKZ | P3 0.143; P2 0.143; CG-D 0.169 |
| 100, 0.1 | 2024 II.KURK | P3 0.145; P2 0.145; CG-D 0.161 |
| 100, 0.1 | KZ network | P3 0.137; P2 0.137; CG-D 0.161 |
| 100, 0.25 | extended IU.MAKZ | P3 0.297; P2 0.297; CG(c=0.5) 0.309 |
| 100, 0.25 | extended II.KURK | P3 0.321; P2 0.321; CG(c=0.5) 0.346 |
| 100, 0.25 | 2024 IU.MAKZ | P3 0.283; P2 0.283; CG-D 0.301 |
| 100, 0.25 | 2024 II.KURK | P3 0.288; P2 0.288; CG-D 0.299 |
| 100, 0.25 | KZ network | P3 0.278; P2 0.278; CG-D 0.293 |
| 100, 0.5 | extended IU.MAKZ | P3 0.516; P2 0.516; CG(c=0.5) 0.527 |
| 100, 0.5 | extended II.KURK | P3 0.548; P2 0.548; CG(c=0.5) 0.575 |
| 100, 0.5 | 2024 IU.MAKZ | P3 0.509; P2 0.509; CG-D 0.520 |
| 100, 0.5 | 2024 II.KURK | P3 0.522; P2 0.522; CG-D 0.532 |
| 100, 0.5 | KZ network | P3 0.505; P2 0.505; CG-D 0.513 |
