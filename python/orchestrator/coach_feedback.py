"""
Coach Feedback Generator - Natural Language Feedback with POTS Voice

Generates coach feedback in the Poet on the Stage (POTS) guidebook voice:
- Direct and encouraging, never condescending
- Uses spoken word terminology ("waking the spirit", "landing the moment")
- Culturally aware - for poets, not corporate presenters
- Focuses on growth, not criticism
- Speaks to the performer as a fellow artist

Supports two modes:
1. Template-based fallback (default) - structured feedback from score data
2. OpenAI GPT integration - dynamic, context-aware feedback (optional)
"""

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .report_generator import PerformanceReport

logger = logging.getLogger(__name__)


# Score tier boundaries for template selection
HIGH_SCORE = 4.0    # 4.0-5.0: Celebrating strengths
MID_SCORE = 2.8     # 2.8-3.9: Building on foundation
                     # 1.0-2.7: Gentle growth coaching


class CoachFeedbackGenerator:
    """
    Generates natural language coach feedback.

    This class is designed for OpenAI GPT integration.
    Currently uses template-based fallback, but the generate_feedback()
    method can be swapped to use GPT-4 for more dynamic responses.
    """

    def __init__(
        self,
        use_openai: bool = False,
        openai_api_key: Optional[str] = None,
    ):
        self.use_openai = use_openai
        self.openai_client = None

        if use_openai and openai_api_key:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                logger.info("OpenAI client initialized for coach feedback")
            except ImportError:
                logger.warning(
                    "openai package not installed. Falling back to templates. "
                    "Install with: pip install openai"
                )
                self.use_openai = False

    def generate_feedback(
        self,
        report: "PerformanceReport",
        engine: str,
        voice: str = "pots",
    ) -> str:
        """
        Generate coach feedback for a specific engine or overall.

        Args:
            report: PerformanceReport with scores and data
            engine: "spirit", "chest", "body", "audience", or "overall"
            voice: Voice/persona to use (default: "pots")

        Returns:
            Natural language feedback string
        """
        if self.use_openai and self.openai_client:
            return self._generate_with_openai(report, engine, voice)
        return self._generate_with_templates(report, engine)

    # =========================================================================
    # OpenAI GPT Integration
    # =========================================================================

    def _generate_with_openai(
        self,
        report: "PerformanceReport",
        engine: str,
        voice: str,
    ) -> str:
        """Generate feedback using OpenAI GPT."""
        prompt = self._build_openai_prompt(report, engine)
        system_prompt = self._build_system_prompt(voice)

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI feedback generation failed: {e}")
            logger.info("Falling back to template-based feedback")
            return self._generate_with_templates(report, engine)

    def _build_system_prompt(self, voice: str) -> str:
        """Build the system prompt for OpenAI with POTS voice instructions."""
        return (
            "You are a spoken word performance coach using the POTS (Poet on the Stage) "
            "methodology. Your voice is:\n"
            "- Direct and encouraging, never condescending\n"
            "- You use spoken word terminology: 'waking the spirit', 'landing the moment', "
            "'breath is life', 'let it breathe', 'the audience needs to feel it'\n"
            "- Culturally aware - you're coaching POETS, not corporate presenters\n"
            "- Focused on growth, not criticism. Every note is about getting better.\n"
            "- You speak to the performer as a fellow artist who has walked this path\n"
            "- You capitalize words for EMPHASIS, use conversational rhythm\n"
            "- Keep feedback to 2-4 sentences. Punchy. Real. Specific.\n"
            "- Reference specific timestamps when available\n"
            "- Never use corporate jargon. This is ART.\n"
        )

    def _build_openai_prompt(
        self,
        report: "PerformanceReport",
        engine: str,
    ) -> str:
        """Build the data prompt for OpenAI GPT."""
        if engine == "overall":
            return (
                f"Generate an overall coach summary for this spoken word performance.\n\n"
                f"Overall Score: {report.overall_score:.1f}/5 ({report.overall_grade})\n"
                f"Spirit: {report.spirit_score:.1f}/5\n"
                f"Chest: {report.chest_score:.1f}/5\n"
                f"Body: {report.body_score:.1f}/5\n"
                f"Audience: {report.audience_score:.1f}/5\n\n"
                f"Top strengths: {', '.join(report.top_strengths)}\n"
                f"Growth areas: {', '.join(report.growth_areas)}\n\n"
                f"Give a 3-5 sentence overall assessment. Start with what's working, "
                f"then address what needs growth. End with encouragement."
            )

        score_map = {
            "spirit": (report.spirit_score, report.spirit_subscores),
            "chest": (report.chest_score, report.chest_subscores),
            "body": (report.body_score, report.body_subscores),
            "audience": (report.audience_score, report.audience_subscores),
        }

        score, subscores = score_map.get(engine, (0, {}))
        sub_str = ", ".join(f"{k}: {v:.1f}" for k, v in subscores.items())

        engine_context = {
            "spirit": "emotional authenticity and alignment between words and feelings",
            "chest": "vocal technique including breath control, projection, and pause mastery",
            "body": "physical performance including gestures, stage presence, and eye contact",
            "audience": "audience engagement including direct address, pacing, and emotional invitation",
        }

        return (
            f"Generate coach feedback for the {engine.upper()} pillar.\n\n"
            f"This pillar measures: {engine_context.get(engine, engine)}\n"
            f"Score: {score:.1f}/5\n"
            f"Sub-scores: {sub_str}\n\n"
            f"Give 2-3 sentences of feedback in POTS voice. "
            f"{'Celebrate what is working.' if score >= HIGH_SCORE else ''}"
            f"{'Be encouraging but honest about what needs work.' if score < MID_SCORE else ''}"
        )

    # =========================================================================
    # Template-Based Fallback
    # =========================================================================

    def _generate_with_templates(
        self,
        report: "PerformanceReport",
        engine: str,
    ) -> str:
        """Generate feedback using POTS-voiced templates."""
        generators = {
            "spirit": self._spirit_feedback,
            "chest": self._chest_feedback,
            "body": self._body_feedback,
            "audience": self._audience_feedback,
            "overall": self._overall_feedback,
        }

        generator = generators.get(engine)
        if generator is None:
            return f"No feedback template for engine: {engine}"

        return generator(report)

    def _spirit_feedback(self, report: "PerformanceReport") -> str:
        """Generate Spirit Engine feedback in POTS voice."""
        score = report.spirit_score
        subs = report.spirit_subscores

        if score >= HIGH_SCORE:
            alignment = subs.get("emotion_alignment", 0)
            range_score = subs.get("range", 0)
            if alignment >= 4.0 and range_score >= 4.0:
                return (
                    "Your spirit is AWAKE. The emotions aren't just in the words - "
                    "they're living in your voice. That emotional range? Chef's kiss. "
                    "You're not performing - you're channeling. Keep that raw authenticity flowing."
                )
            return (
                "The spirit is alive and moving. I can feel you LIVING in this piece - "
                "the emotions are hitting, the transitions are landing. "
                "This is what it looks like when a poet and their piece become one."
            )

        if score >= MID_SCORE:
            weakest = min(subs, key=subs.get) if subs else "alignment"
            weak_notes = {
                "emotion_alignment": (
                    "I hear the words, but sometimes the emotion doesn't quite match. "
                    "When you say something heavy, I need to FEEL that weight in your voice. "
                    "Close your eyes, remember what made you write this, and let that truth out."
                ),
                "transitions": (
                    "The individual emotions are there, but the bridges between them need work. "
                    "You're jumping from feeling to feeling like channel surfing. "
                    "Let each transition be a JOURNEY, not a teleport."
                ),
                "range": (
                    "You're playing it safe emotionally. I know there's more in there. "
                    "This piece has mountain peaks and deep valleys - "
                    "right now you're walking the foothills. Go THERE."
                ),
                "settling": (
                    "The spirit is stirring but hasn't fully woken up yet. "
                    "I hear the words, but I'm not feeling them land in your body. "
                    "Live with this piece more. Let it settle into your bones."
                ),
            }
            return weak_notes.get(weakest, (
                "The spirit is building. There are moments where I feel it CLICK - "
                "hold onto those. The foundation is solid, now we need consistency."
            ))

        # Low score
        return (
            "The spirit is stirring but hasn't fully woken up yet. "
            "I hear the words, but I'm not feeling them land in your body. "
            "Here's what I want you to try: before you perform, close your eyes "
            "and remember WHY you wrote this. Who is it for? What does it NEED to say? "
            "Let that truth be your fuel. The technique will follow the intention."
        )

    def _chest_feedback(self, report: "PerformanceReport") -> str:
        """Generate Chest Engine feedback in POTS voice."""
        score = report.chest_score
        subs = report.chest_subscores

        if score >= HIGH_SCORE:
            return (
                "Your vocal technique is SOLID. The breath control is there, "
                "the projection fills the room, and you're using silence like a weapon. "
                "This is what it sounds like when a poet has done the work. "
                "Your instrument is tuned and ready."
            )

        if score >= MID_SCORE:
            weakest = min(subs, key=subs.get) if subs else "breath_control"
            weak_notes = {
                "breath_control": (
                    "Your breath is your foundation, and right now it's a bit shaky. "
                    "I hear you running out of air on the longer lines - "
                    "those lines deserve FULL lungs behind them. "
                    "Breath is life. Control the breath, control the room."
                ),
                "projection": (
                    "I need MORE from your voice. Not louder - more PRESENT. "
                    "The back row is leaning in trying to hear you. "
                    "Project from your chest, not your throat. "
                    "Let the room feel every word."
                ),
                "pause_technique": (
                    "You're filling every second with sound. "
                    "Silence is not the enemy - it's your secret weapon. "
                    "After a big line, STOP. Let the audience catch up. "
                    "The pause is where the meaning lives."
                ),
                "vocal_health": (
                    "I'm hearing some strain in your voice. Your instrument matters. "
                    "Don't push from your throat - let the sound come from your chest. "
                    "Warm up before you perform. Hydrate. "
                    "Your voice has to last as long as your career."
                ),
            }
            return weak_notes.get(weakest, (
                "The vocal foundation is building. There are moments where "
                "the technique shines through - now we need that consistency "
                "from the first word to the last."
            ))

        return (
            "Let's talk about your instrument - your voice. "
            "Right now it needs some tuning. The breath control is the foundation "
            "of everything else, and we need to build that up. "
            "Start with this: before your next performance, do 5 minutes of "
            "breathing exercises. In for 4, hold for 4, out for 4. "
            "Your voice will thank you."
        )

    def _body_feedback(self, report: "PerformanceReport") -> str:
        """Generate Body Engine feedback in POTS voice."""
        score = report.body_score
        subs = report.body_subscores

        if score >= HIGH_SCORE:
            return (
                "Your body is IN it. The gestures aren't decoration - "
                "they're part of the story. That stage presence? "
                "You're not just standing there, you're COMMANDING the space. "
                "The physical and the vocal are dancing together. Beautiful."
            )

        if score >= MID_SCORE:
            weakest = min(subs, key=subs.get) if subs else "gesture_intentionality"
            weak_notes = {
                "gesture_intentionality": (
                    "Some of those gestures are working FOR you, and some are just... nervous energy. "
                    "I want every hand movement to MEAN something. "
                    "If your words say 'I reached out,' your hands should know where they're going."
                ),
                "stage_presence": (
                    "You've got the mic, but you're not owning the space yet. "
                    "The stage is yours - ALL of it. Don't just stand at the mic stand. "
                    "Take a step. Claim the room. "
                    "Your physical confidence tells the audience they can trust you."
                ),
                "eye_contact": (
                    "Look at them. No, really LOOK at them. "
                    "Right now your eyes are everywhere except the audience. "
                    "Pick one person. Speak a line to THEM. Then another person. "
                    "Eye contact is how you pull them into your world."
                ),
                "physical_vocal_sync": (
                    "Your body and your voice are having two different conversations. "
                    "When the words say POWER, your body should feel it. "
                    "When the words say 'tender,' your body should soften. "
                    "Let the truth of the words move through your whole body."
                ),
            }
            return weak_notes.get(weakest, (
                "The body is starting to join the party. "
                "There are moments where the physical and the vocal line up - "
                "and those moments are POWERFUL. Let's get more of those."
            ))

        return (
            "Your body is just... standing there while your words do all the work. "
            "Let it IN. Your words are telling a story that your body needs to "
            "help tell. You don't need choreography - just let the truth move through you. "
            "Start small: one intentional gesture per stanza. "
            "Let your body learn what your mouth already knows."
        )

    def _audience_feedback(self, report: "PerformanceReport") -> str:
        """Generate Audience Engine feedback in POTS voice."""
        score = report.audience_score
        subs = report.audience_subscores

        if score >= HIGH_SCORE:
            return (
                "You're not just performing - you're CONNECTING. "
                "The audience isn't watching you, they're WITH you. "
                "That direct address? That pacing that lets every line land? "
                "This is what engagement looks like. The room is yours."
            )

        if score >= MID_SCORE:
            weakest = min(subs, key=subs.get) if subs else "direct_address"
            weak_notes = {
                "direct_address": (
                    "Right now you're performing AT the audience, not WITH them. "
                    "I want you to imagine one person in that front row - "
                    "your best friend, your grandmother, someone who GETS it. "
                    "Speak TO them. Make it personal."
                ),
                "pacing": (
                    "You're moving too fast for the audience to keep up. "
                    "Every powerful line needs a moment to LAND. "
                    "Think of it like music - the rests are as important as the notes. "
                    "Give the audience time to feel what you just said."
                ),
                "emotional_invitation": (
                    "You're telling the audience about your emotions, "
                    "but you're not inviting them to FEEL with you. "
                    "There's a difference between 'I was sad' and letting sadness "
                    "fill the room. Open the door. Let them in."
                ),
                "engagement_patterns": (
                    "Your delivery is a bit one-note right now. "
                    "The audience needs peaks and valleys - moments of fire "
                    "and moments of whisper. Vary your energy to keep them locked in. "
                    "Surprise them."
                ),
            }
            return weak_notes.get(weakest, (
                "The audience connection is building. "
                "There are moments where the room gets quiet - that's them listening. "
                "Now let's make the WHOLE performance that magnetic."
            ))

        return (
            "Right now it feels like you're reciting in a mirror rather than "
            "performing for people. And that's okay - that's where a lot of poets start. "
            "Here's the shift: pick ONE person in the audience (real or imagined) "
            "and deliver the whole piece to THEM. "
            "When you make it personal, the whole room feels it."
        )

    def _overall_feedback(self, report: "PerformanceReport") -> str:
        """Generate overall coach summary in POTS voice."""
        score = report.overall_score
        grade = report.overall_grade

        # Identify strongest and weakest engines
        engine_scores = {
            "spirit": report.spirit_score,
            "chest": report.chest_score,
            "body": report.body_score,
            "audience": report.audience_score,
        }

        # Filter out engines with 0 score (not available)
        active = {k: v for k, v in engine_scores.items() if v > 0}

        if not active:
            return (
                "We couldn't fully analyze this performance yet. "
                "Make sure we have good video and audio to work with, "
                "and let's try again. Every performance is a chance to grow."
            )

        strongest = max(active, key=active.get)
        weakest = min(active, key=active.get)

        strong_name = {
            "spirit": "emotional authenticity",
            "chest": "vocal technique",
            "body": "physical presence",
            "audience": "audience connection",
        }

        if score >= HIGH_SCORE:
            return (
                f"Here's the real talk: you're doing the WORK and it shows. "
                f"Your {strong_name[strongest]} is leading the way at "
                f"{active[strongest]:.1f}/5 - that's the foundation everything else "
                f"builds on. The overall {grade}? That's not just a score, "
                f"that's proof you're growing into the performer you're meant to be. "
                f"Keep pushing. Keep creating. The stage needs you."
            )

        if score >= MID_SCORE:
            pct = int((score / 5.0) * 100)
            return (
                f"Here's the real talk: You've got something. "
                f"Your {strong_name[strongest]} is your superpower right now. "
                f"But we need to bring the {strong_name[weakest]} up to match. "
                f"You're {pct}% there. "
                f"Focus on: (1) {report.growth_areas[0] if report.growth_areas else 'breathing'}, "
                f"(2) {report.growth_areas[1] if len(report.growth_areas) > 1 else 'presence'}, "
                f"(3) {report.growth_areas[2] if len(report.growth_areas) > 2 else 'connection'}. "
                f"The talent is there. Let's sharpen it."
            )

        return (
            f"Every master was once a beginner, and every performance is a step forward. "
            f"Your {strong_name[strongest]} shows me there's real potential here. "
            f"Right now, I want you to focus on just ONE thing: "
            f"{report.growth_areas[0] if report.growth_areas else 'connecting with your audience'}. "
            f"Don't try to fix everything at once. "
            f"Master one element, and the others will start to follow. "
            f"I believe in where this is going."
        )
