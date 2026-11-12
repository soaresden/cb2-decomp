# Free Style "lift": at the finish line the run counts as usual (ranking, records, trophies -- e.g. for Snowman), but
# the FINISH celebration and the replay (about 15 s) are skipped: straight to the ranking (START), then the RESULTS
# screen with the run's time and RETRY selected (X): instant restart at the top of the course, no loading.
# How: the race exit code 5 (finish) is handled at 0x8005D548: it counts the finishers, then calls func_80074768
# (celebration + replay, returns -1 = "show the results" when START is pressed). The call is replaced by its result.
# See docs/freestyle_lift.md.
HOOK = 0x8005d5a4
HOOK_OLD = 0x0c01d1da            # jal func_80074768
NEW = 0x2402ffff                 # addiu v0, zero, -1

def patches():
    return [('/FREE.BIN', HOOK, HOOK_OLD, NEW)]
