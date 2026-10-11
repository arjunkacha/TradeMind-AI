Yes — that's only the function header. We need the body too.

Please copy from:

def calculate_decision(
    risk_score,
    risk_level,
    behaviors,
    discipline_score,
):

all the way down to the end of that function, including the lines with:

if discipline_score < 20:

and the final:

return decision, recommendation

Paste that whole function here. Then I'll give you the exact replacement code to paste in.

decision_engine(1).py
Python
here is desicion_engine.py file

Perfect. I found the exact problem in your current decision_engine.py.

The issue is here: your engine always uses discipline_score for the override, even when that score is invalid. The function currently does:

if discipline_score < 20:

So when TradingView gives:

discipline_score = 0
discipline_score_valid = false

the engine still sees 0 < 20 and changes:

ALLOW → CAUTION

That explains the result you're seeing. The ML signal is not the cause; your own discipline override is.

Step 1 — Replace calculate_decision()

In decision_engine.py, replace the entire function from:

def calculate_decision(

through:

return decision, recommendation

with:

def calculate_decision(
    risk_score,
    risk_level,
    behaviors,
    discipline_score,
    discipline_score_valid=False,
):

    behavior_count = len(behaviors)

    # --------------------------------------------------------
    # CRITICAL
    # --------------------------------------------------------

    if (
        risk_level == "CRITICAL"
        or risk_score >= CRITICAL_RISK_THRESHOLD
    ):

        decision = "DO NOT TRADE"

        recommendation = (
            "Stop trading and enter a cooldown period. "
            "Multiple high-risk conditions are present."
        )

    # --------------------------------------------------------
    # HIGH
    # --------------------------------------------------------

    elif (
        risk_level == "HIGH"
        or risk_score >= HIGH_RISK_THRESHOLD
    ):

        decision = "AVOID / REDUCE RISK"

        recommendation = (
            "Avoid the trade or significantly reduce "
            "position size until behavior stabilizes."
        )

    # --------------------------------------------------------
    # MEDIUM
    # --------------------------------------------------------

    elif risk_level == "MEDIUM":

        decision = "CAUTION"

        recommendation = (
            "Trade only with controlled position sizing "
            "and strict risk management."
        )

    # --------------------------------------------------------
    # LOW
    # --------------------------------------------------------

    else:

        decision = "ALLOW"

        recommendation = (
            "No major behavioral risk detected. "
            "Normal risk controls should still apply."
        )

    # --------------------------------------------------------
    # DISCIPLINE OVERRIDE
    # --------------------------------------------------------
    # IMPORTANT:
    # Never use an invalid/missing discipline score
    # to override the risk-based decision.
    # --------------------------------------------------------

    if (
        discipline_score_valid
        and discipline_score is not None
        and discipline_score < 20
    ):

        if decision == "ALLOW":
            decision = "CAUTION"

        recommendation += (
            " Trader discipline is currently very low."
        )

    # --------------------------------------------------------
    # MULTIPLE BEHAVIORS
    # --------------------------------------------------------

    if behavior_count >= 3:

        if decision != "DO NOT TRADE":
            decision = "AVOID / REDUCE RISK"

        recommendation += (
            " Multiple behavioral patterns were detected."
        )

    return decision, recommendation
Step 2 — Update build_decisions()

Now find this section around your current lines 510–525:

profile = profile_lookup.get(
    account,
    {
        "discipline_score": 50,
        "primary_risk": "None",
        "win_rate": 0,
        "average_risk_score": 0,
    }
)

discipline_score = float(
    profile["discipline_score"]
)

Replace it with:

profile = profile_lookup.get(
    account,
    {
        "discipline_score": 50,
        "discipline_score_valid": False,
        "primary_risk": "None",
        "win_rate": 0,
        "average_risk_score": 0,
    }
)

raw_discipline_score = profile.get(
    "discipline_score",
    50
)

try:
    discipline_score = float(raw_discipline_score)
except (TypeError, ValueError):
    discipline_score = 50.0

discipline_score_valid = bool(
    profile.get(
        "discipline_score_valid",
        False
    )
)
Step 3 — Update the function call

Find:

decision, recommendation = calculate_decision(
    risk_score,
    risk_level,
    detected_behaviors,
    discipline_score,
)

Change it to:

decision, recommendation = calculate_decision(
    risk_score,
    risk_level,
    detected_behaviors,
    discipline_score,
    discipline_score_valid,
)
Step 4 — One more important change

Your get_profile_lookup() currently only returns:

"discipline_score"
"primary_risk"
"win_rate"
"average_risk_score"

We should also carry the validity flag.

Find:

lookup[row["account"]] = {
    "discipline_score": row.get(
        "discipline_score",
        50
    ),

and add immediately after it:

"discipline_score_valid": row.get(
    "discipline_score_valid",
    False
),

So that section becomes:

lookup[row["account"]] = {

    "discipline_score": row.get(
        "discipline_score",
        50
    ),

    "discipline_score_valid": row.get(
        "discipline_score_valid",
        False
    ),

    "primary_risk": row.get(
        "primary_risk",
        "None"
    ),

    "win_rate": row.get(
        "win_rate",
        0
    ),

    "average_risk_score": row.get(
        "average_risk_score",
        0
    ),
}

This keeps the decision engine consistent with the validity information you're already exposing in the API. Your current engine's decision logic and profile lookup are exactly where this needs to be addressed.

Why we're doing this

For your test trade:

Risk Score:             0
Risk Level:             LOW
Behaviors:              0
Discipline Score:       0
Discipline Valid:       FALSE
ML Win Probability:     29.6%
ML Signal:              LOW WIN PROBABILITY

The engine should not treat the invalid 0 discipline score as a real discipline measurement.

And importantly, your architecture explicitly says the ML model is a supporting signal, while behavioral/risk rules remain the primary decision mechanism.

So don't change the ML logic yet.

Make these 3 edits, save decision_engine.py, and tell me done. Then we'll regenerate the TradingView analysis and test TV-8AA5709BA03E again.

give me the full updated desicion_engine.oy file.. with updated cpde
Analysis errored
from pathlib import Path

src = Path("/mnt/data/decision_engine(1).py")
text = src.read_text(encoding="utf-8")

old = '''def calculate_decision(
    risk_score,
    risk_level,
    behaviors,
    discipline_score,
):

    behavior_count = len(behaviors)

    # --------------------------------------------------------
    # CRITICAL
    # --------------------------------------------------------

    if (
        risk_level == "CRITICAL"
        or risk_score >= CRITICAL_RISK_THRESHOLD
    ):

        decision = "DO NOT TRADE"

        recommendation = (
            "Stop trading and enter a cooldown period. "
            "Multiple high-risk conditions are present."
        )

    # --------------------------------------------------------
    # HIGH
    # --------------------------------------------------------

    elif (
        risk_level == "HIGH"
        or risk_score >= HIGH_RISK_THRESHOLD
    ):

        decision = "AVOID / REDUCE RISK"

        recommendation = (
            "Avoid the trade or significantly reduce "
            "position size until behavior stabilizes."
        )

    # --------------------------------------------------------
    # MEDIUM
    # --------------------------------------------------------

    elif risk_level == "MEDIUM":

        decision = "CAUTION"

        recommendation = (
            "Trade only with controlled position sizing "
            "and strict risk management."
        )

    # --------------------------------------------------------
    # LOW
    # --------------------------------------------------------

    else:

        decision = "ALLOW"

        recommendation = (
            "No major behavioral risk detected. "
            "Normal risk controls should still apply."
        )

    # --------------------------------------------------------
    # DISCIPLINE OVERRIDE
    # --------------------------------------------------------

    if discipline_score < 20:

        if decision == "ALLOW":
            decision = "CAUTION"

        recommendation += (
            " Trader discipline is currently very low."
        )

    # --------------------------------------------------------
    # MULTIPLE BEHAVIORS
    # --------------------------------------------------------

    if behavior_count >= 3:

        if decision != "DO NOT TRADE":
            decision = "AVOID / REDUCE RISK"

        recommendation += (
            " Multiple behavioral patterns were detected."
        )

    return decision, recommendation
'''

new = '''def calculate_decision(
    risk_score,
    risk_level,
    behaviors,
    discipline_score,
    discipline_score_valid=False,
):

    behavior_count = len(behaviors)

    # --------------------------------------------------------
    # CRITICAL
    # --------------------------------------------------------

    if (
        risk_level == "CRITICAL"
        or risk_score >= CRITICAL_RISK_THRESHOLD
    ):

        decision = "DO NOT TRADE"

        recommendation = (
            "Stop trading and enter a cooldown period. "
            "Multiple high-risk conditions are present."
        )

    # --------------------------------------------------------
    # HIGH
    # --------------------------------------------------------

    elif (
        risk_level == "HIGH"
        or risk_score >= HIGH_RISK_THRESHOLD
    ):

        decision = "AVOID / REDUCE RISK"

        recommendation = (
            "Avoid the trade or significantly reduce "
            "position size until behavior stabilizes."
        )

    # --------------------------------------------------------
    # MEDIUM
    # --------------------------------------------------------

    elif risk_level == "MEDIUM":

        decision = "CAUTION"

        recommendation = (
            "Trade only with controlled position sizing "
            "and strict risk management."
        )

    # --------------------------------------------------------
    # LOW
    # --------------------------------------------------------

    else:

        decision = "ALLOW"

        recommendation = (
            "No major behavioral risk detected. "
            "Normal risk controls should still apply."
        )

    # --------------------------------------------------------
    # DISCIPLINE OVERRIDE
    # --------------------------------------------------------
    # IMPORTANT:
    # An invalid or unavailable discipline score must never
    # override the risk-based decision.
    # --------------------------------------------------------

    if (
        discipline_score_valid
        and discipline_score is not None
        and discipline_score < 20
    ):

        if decision == "ALLOW":
            decision = "CAUTION"

        recommendation += (
            " Trader discipline is currently very low."
        )

    # --------------------------------------------------------
    # MULTIPLE BEHAVIORS
    # --------------------------------------------------------

    if behavior_count >= 3:

        if decision != "DO NOT TRADE":
            decision = "AVOID / REDUCE RISK"

        recommendation += (
            " Multiple behavioral patterns were detected."
        )

    return decision, recommendation
'''

if old not in text:
    raise ValueError("calculate_decision block not found")

text = text.replace(old, new)

old_profile = '''            "discipline_score": row.get(
                "discipline_score",
                50
            ),

            "primary_risk": row.get(
'''
new_profile = '''            "discipline_score": row.get(
                "discipline_score",
                50
            ),

            "discipline_score_valid": row.get(
                "discipline_score_valid",
                False
            ),

            "primary_risk": row.get(
'''

if old_profile not in text:
    raise ValueError("profile lookup block not found")

text = text.replace(old_profile, new_profile)

old_build = '''        profile = profile_lookup.get(
            account,
            {
                "discipline_score": 50,
                "primary_risk": "None",
                "win_rate": 0,
                "average_risk_score": 0,
            }
        )

        discipline_score = float(
            profile["discipline_score"]
        )

        primary_risk = profile[
'''

new_build = '''        profile = profile_lookup.get(
            account,
            {
                "discipline_score": 50,
                "discipline_score_valid": False,
                "primary_risk": "None",
                "win_rate": 0,
                "average_risk_score": 0,
            }
        )

        raw_discipline_score = profile.get(
            "discipline_score",
            50
        )

        try:
            discipline_score = float(
                raw_discipline_score
            )
        except (TypeError, ValueError):
            discipline_score = 50.0

        discipline_score_valid = bool(
            profile.get(
                "discipline_score_valid",
                False
            )
        )

        primary_risk = profile[
'''

if old_build not in text:
    raise ValueError("build profile block not found")

text = text.replace(old_build, new_build)

old_call = '''        ) = calculate_decision(

            risk_score,

            risk_level,

            detected_behaviors,

            discipline_score,
        )
'''

new_call = '''        ) = calculate_decision(

            risk_score,

            risk_level,

            detected_behaviors,

            discipline_score,

            discipline_score_valid,
        )
'''

if old_call not in text:
    raise ValueError("calculate_decision call block not found")

text = text.replace(old_call, new_call)

out = Path("/mnt/data/decision_engine_UPDATED.py")
out.write_text(text, encoding="utf-8")

print(f"Created: {out}")
print("Updated discipline-score validation in get_profile_lookup(), calculate_decision(), and build_decisions().")