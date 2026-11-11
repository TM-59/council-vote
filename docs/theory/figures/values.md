# Measured values

Written by `make theory-figs` (scripts/theory_figs.py) from the domain itself. Do not edit by hand.
The last column is the relative error; where the theory column is 0 it is the absolute value.

| id | what is measured | measured | theory | error |
|---|---|---|---|---|
| `agendas` | different agendas, enumerated (theory 2^3) | 8 | 8 | 0.00e+00 |
| `agenda-rejected` | of four non-boolean clause values, how many raise TypeError (theory 4) | 4 | 4 | 0.00e+00 |
| `seats` | seats in the three fixed councils (theory 15) | 15 | 15 | 0.00e+00 |
| `seat-one-ballot` | every seat gives exactly one ballot for every agenda, 15 x 8 cases (1 = yes) | 1 | 1 | 0.00e+00 |
| `seat-abstainers` | seats that have an abstaining condition | 8 | 0 | 8.00e+00 |
| `seat-abstain-first` | cases where the abstaining condition holds but the ballot is not an abstention (theory 0) | 0 | 0 | 0.00e+00 |
| `count-splits` | ordered ways five seats can vote, enumerated (theory 3^5) | 243 | 243 | 0.00e+00 |
| `count-rule` | of them, cases where the counter disagrees with 'at least three take part and yes exceeds no' (theory 0) | 0 | 0 | 0.00e+00 |
| `count-approved` | of them, cases that approve the agenda | 81 | 0 | 8.10e+01 |
| `count-tie` | approved for two yes, two no, one abstention (theory 0: a tie is rejected) | 0 | 0 | 0.00e+00 |
| `count-no-quorum` | approved for two yes, three abstentions (theory 0: no quorum) | 0 | 0 | 0.00e+00 |
| `count-three-one` | approved for three yes, one no, one abstention (theory 1) | 1 | 1 | 0.00e+00 |
| `council-1-passing` | agendas of eight that pass council 1, Harbour Wardens | 3 | 0 | 3.00e+00 |
| `council-2-passing` | agendas of eight that pass council 2, Night Watch | 2 | 0 | 2.00e+00 |
| `council-3-passing` | agendas of eight that pass council 3, Guild Elders | 2 | 0 | 2.00e+00 |
| `council-common` | agendas that pass all three councils (theory 0: each council must be read) | 0 | 0 | 0.00e+00 |
| `play-lost-1` | plans that end lost at council 1 | 102400 | 0 | 1.02e+05 |
| `play-lost-2` | plans that end lost at council 2 | 89856 | 0 | 8.99e+04 |
| `play-lost-3` | plans that end lost at council 3 | 39312 | 0 | 3.93e+04 |
| `play-won` | plans that win | 30576 | 0 | 3.06e+04 |
| `play-plans` | plans of six agendas played through the aggregate (theory 8^6) | 262144 | 262144 | 0.00e+00 |
| `play-all-finish` | of them, plans after which the session is finished (theory all: six agendas always suffice) | 262144 | 262144 | 0.00e+00 |
| `play-win-chance` | fraction of plans that win: the chance of winning by picking agendas at random (theory: product over councils of 1 - (1 - p)^2) | 0.11663818 | 0.11663818 | 0.00e+00 |
| `play-informed` | outcome of the player who reads the conditions and proposes a passing agenda each time (1 = won in three) | 1 | 1 | 0.00e+00 |
| `attempt-cost` | attempts left after one rejected agenda (theory 1) | 1 | 1 | 0.00e+00 |
| `attempt-restored` | attempts left after an approval moves to the next council (theory 2) | 2 | 2 | 0.00e+00 |
| `events-on-loss` | events returned by the losing resolution (theory 2: AgendaResolved, SessionEnded) | 2 | 2 | 0.00e+00 |
| `finished-refuses` | a finished session raises SessionFinished (theory 1) | 1 | 1 | 0.00e+00 |
| `finished-history` | resolutions recorded after that refusal (theory 2: nothing was added) | 2 | 2 | 0.00e+00 |
| `invalid-free` | attempts left after a proposal that is not an Agenda (theory 2: none consumed) | 2 | 2 | 0.00e+00 |
