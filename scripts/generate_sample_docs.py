#!/usr/bin/env python3
"""
Generate sample PDF knowledge documents about the Universe and Planet Zephyria
for use with Vertex AI Search RAG solution.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'knowledge_base')
os.makedirs(OUTPUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()
title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=24, spaceAfter=20, alignment=TA_CENTER, textColor=colors.HexColor('#1a237e'))
h1_style = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=16, spaceAfter=12, textColor=colors.HexColor('#283593'))
h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, spaceAfter=10, textColor=colors.HexColor('#3949ab'))
body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, spaceAfter=8, leading=16, alignment=TA_JUSTIFY)
note_style = ParagraphStyle('Note', parent=styles['Normal'], fontSize=10, spaceAfter=8, leading=14, textColor=colors.HexColor('#555555'), leftIndent=20)


def make_doc(filename, content_fn):
    path = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(path, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    story = []
    content_fn(story)
    doc.build(story)
    print(f"Created: {path}")


# ─────────────────────────────────────────────
# DOC 1: The Universe – An Overview
# ─────────────────────────────────────────────
def doc_universe(story):
    story.append(Paragraph("The Universe: An Overview", title_style))
    story.append(Paragraph("A Comprehensive Guide to Cosmic Knowledge", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=13, alignment=TA_CENTER, textColor=colors.grey)))
    story.append(Spacer(1, 0.3*inch))

    sections = [
        ("What is the Universe?",
         "The Universe is all of space, time, matter, and energy that exists. It encompasses everything from subatomic particles to vast galaxy superclusters. Current scientific consensus holds that the Universe began approximately 13.8 billion years ago in an event known as the Big Bang — a rapid expansion from an extremely hot and dense initial state."),
        ("Scale and Structure",
         "The observable Universe spans roughly 93 billion light-years in diameter. Within this vast expanse, matter is organized hierarchically: planets orbit stars, stars form galaxies, galaxies cluster into groups and superclusters, and superclusters form the cosmic web — filaments of dark matter and gas threading through vast cosmic voids."),
        ("Galaxies",
         "There are an estimated 2 trillion galaxies in the observable Universe. Our own galaxy, the Milky Way, contains 100-400 billion stars and spans about 100,000 light-years. Galaxies come in various shapes: spiral (like the Milky Way), elliptical, and irregular. Most large galaxies harbor a supermassive black hole at their center."),
        ("Stars and Stellar Life Cycles",
         "Stars are massive balls of plasma held together by gravity and powered by nuclear fusion. They form from collapsing clouds of gas and dust called nebulae. A star's life cycle depends on its mass: low-mass stars like our Sun become red giants and then white dwarfs, while massive stars explode as supernovae, sometimes leaving behind neutron stars or black holes."),
        ("Planets and Solar Systems",
         "Planets form from the disk of gas and dust surrounding young stars (protoplanetary disks). Our Solar System contains 8 planets, dozens of moons, and billions of smaller bodies. Astronomers have discovered over 5,500 exoplanets orbiting other stars, with thousands more candidates awaiting confirmation."),
        ("Dark Matter and Dark Energy",
         "Ordinary matter makes up only about 5% of the Universe. Dark matter (≈27%) is an invisible substance that exerts gravity but does not interact with light. Dark energy (≈68%) is a mysterious force driving the accelerating expansion of the Universe. Neither dark matter nor dark energy has been directly detected; their existence is inferred from their gravitational and cosmological effects."),
        ("The Fate of the Universe",
         "Several hypotheses describe the ultimate fate of the Universe. The most widely accepted is the 'Big Freeze' or Heat Death — as the Universe continues expanding, stars will eventually burn out, black holes will evaporate via Hawking radiation, and entropy will approach its maximum. Other theories include the Big Rip (dark energy tears apart matter) and the Big Crunch (gravity eventually reverses expansion)."),
    ]

    for heading, body in sections:
        story.append(Paragraph(heading, h1_style))
        story.append(Paragraph(body, body_style))
        story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph("Key Facts at a Glance", h1_style))
    data = [
        ["Property", "Value"],
        ["Age of Universe", "~13.8 billion years"],
        ["Observable Diameter", "~93 billion light-years"],
        ["Number of Galaxies", "~2 trillion"],
        ["Stars in Milky Way", "100–400 billion"],
        ["Composition (ordinary matter)", "~5%"],
        ["Dark Matter", "~27%"],
        ["Dark Energy", "~68%"],
        ["Expansion Rate (Hubble Constant)", "~70 km/s/Mpc"],
    ]
    table = Table(data, colWidths=[3*inch, 3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#e8eaf6'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#9fa8da')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('ROWHEIGHT', (0,0), (-1,-1), 20),
    ]))
    story.append(table)


# ─────────────────────────────────────────────
# DOC 2: Planet Zephyria – World Guide
# ─────────────────────────────────────────────
def doc_zephyria_overview(story):
    story.append(Paragraph("Planet Zephyria", title_style))
    story.append(Paragraph("The Living World Beyond the Veil Nebula", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=13, alignment=TA_CENTER, textColor=colors.HexColor('#1b5e20'))))
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("Discovery and Location", h1_style))
    story.append(Paragraph(
        "Zephyria was first detected in 2087 by the Horizon Deep Field telescope array, orbiting in the habitable zone of the binary star system Lyris-7, located 340 light-years from Earth in the constellation Aquila. The planet lies within the outer arm of a spiral galaxy astronomers call the Veil Nebula Cluster (VNC-4412). Its discovery sent shockwaves through the scientific community — spectroscopic analysis of its atmosphere revealed unmistakable biosignatures: oxygen, methane, and complex organic molecules.",
        body_style))

    story.append(Paragraph("Physical Characteristics", h1_style))
    data = [
        ["Characteristic", "Zephyria", "Earth (comparison)"],
        ["Diameter", "14,200 km", "12,742 km"],
        ["Mass", "1.3 Earth masses", "1 Earth mass"],
        ["Surface Gravity", "1.08 g", "1.0 g"],
        ["Orbital Period", "387 Earth days", "365 days"],
        ["Day Length", "28 Earth hours", "24 hours"],
        ["Axial Tilt", "19°", "23.5°"],
        ["Surface Water Coverage", "71%", "71%"],
        ["Average Temperature", "18°C", "15°C"],
        ["Atmospheric Pressure", "1.05 atm", "1 atm"],
        ["Number of Moons", "3 (Aela, Mira, Dusk)", "1"],
    ]
    table = Table(data, colWidths=[2.5*inch, 2*inch, 2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1b5e20')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#e8f5e9'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#a5d6a7')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('ROWHEIGHT', (0,0), (-1,-1), 20),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("Atmosphere", h1_style))
    story.append(Paragraph(
        "Zephyria's atmosphere is remarkably similar to Earth's, composed primarily of nitrogen (74%), oxygen (22%), argon (2%), and trace gases including carbon dioxide, methane, and water vapor. The slightly higher oxygen content gives Zephyrian skies a deeper blue hue during the day, while the triple moons create stunning auroral displays at the poles. A thick ozone layer protects the surface from harmful radiation emitted by its two parent stars.",
        body_style))

    story.append(Paragraph("Geography and Terrain", h1_style))
    story.append(Paragraph(
        "Zephyria has four major continents: Valdris (the largest, spanning the equatorial region), Theron (a temperate northern landmass), Solmara (a tropical archipelago chain), and Umbraxis (a polar continent covered in turquoise ice). The planet is crisscrossed by vast river networks fed by polar meltwater. The Singing Peaks mountain range on Valdris rises to 11,000 meters — taller than Everest — and is named for the haunting resonant tones produced when wind passes through its crystalline rock formations.",
        body_style))

    story.append(Paragraph("Ecology Overview", h1_style))
    story.append(Paragraph(
        "Life on Zephyria is carbon-based, using liquid water as a solvent — mirroring the biochemical foundation of Earth life. However, Zephyrian organisms evolved independently and exhibit strikingly different body plans. The planet supports an estimated 8 million catalogued species, with scientists believing millions more remain undiscovered in the deep oceans and underground cave systems.",
        body_style))


# ─────────────────────────────────────────────
# DOC 3: Zephyrian Life Forms
# ─────────────────────────────────────────────
def doc_zephyria_life(story):
    story.append(Paragraph("Life on Zephyria", title_style))
    story.append(Paragraph("Flora, Fauna, and the Dominant Civilization", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=13, alignment=TA_CENTER, textColor=colors.HexColor('#4a148c'))))
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("Flora", h1_style))
    flora = [
        ("Luminar Trees", "The most iconic plant of Zephyria, Luminar Trees grow up to 60 meters tall with bioluminescent leaves that glow in shades of violet and gold at night. They photosynthesize using both visible and ultraviolet light from the binary star system. Luminar forests cover 40% of Valdris and serve as the primary habitat for hundreds of species."),
        ("Azure Moss", "A ubiquitous ground cover found on all continents, Azure Moss forms dense mats of brilliant blue-green that retain moisture during dry seasons. Zephyrian ecologists consider it the planet's 'biological glue' — preventing soil erosion and anchoring entire ecosystems."),
        ("Crystalline Kelp", "In the deep oceans, Crystalline Kelp grows in vast submarine forests reaching 200 meters. Its cell walls incorporate silicate compounds, giving it a glass-like appearance. It is the foundation of Zephyria's marine food web and is harvested by the Velorians as a food source."),
        ("Whisper Vines", "Found in the cave systems of Umbraxis, Whisper Vines are chemosynthetic — deriving energy from mineral-rich hydrothermal vents rather than sunlight. They are believed to form a rudimentary chemical signalling network spanning kilometers."),
    ]
    for name, desc in flora:
        story.append(Paragraph(name, h2_style))
        story.append(Paragraph(desc, body_style))

    story.append(Paragraph("Fauna", h1_style))
    fauna = [
        ("Skyweavers", "Six-winged aerial creatures resembling a cross between a manta ray and a jellyfish, Skyweavers glide on thermal currents at altitudes up to 5,000 meters. They are filter feeders, consuming atmospheric spores and microorganisms. Their wingspan can reach 4 meters. Skyweavers migrate between continents seasonally and are considered sacred by the Velorian people."),
        ("Thornbacks", "Large hexapedal land animals resembling a rhinoceros crossed with an armadillo. Thornbacks have six legs, a heavily armoured carapace covered in crystalline spines, and a highly developed sense of electromagnetic fields, which they use for navigation and communication. They are herbivores weighing up to 3,000 kg."),
        ("Glowfish", "The seas of Zephyria teem with Glowfish — schooling bioluminescent organisms that communicate through complex light patterns. Researchers have decoded over 200 distinct 'phrases' in their light language, suggesting a rudimentary form of social communication. They are the primary prey of the ocean's apex predators, the Leviathans."),
        ("Leviathans", "The apex marine predators of Zephyria, Leviathans are enormous eel-like creatures reaching 50 meters in length. Despite their fearsome size, they are highly intelligent, exhibiting cooperative hunting strategies and apparent play behaviour. Their calls, transmitted through the water at sub-sonic frequencies, can travel thousands of kilometres."),
        ("Micro-Symbiotes", "Microscopic organisms that live in symbiosis with most large Zephyrian animals, Micro-Symbiotes reside in specialized organs and assist with digestion, immune function, and even cognition. The Velorians have a uniquely dense population of neural micro-symbiotes, which some researchers believe contribute to their remarkable memory and pattern recognition abilities."),
    ]
    for name, desc in fauna:
        story.append(Paragraph(name, h2_style))
        story.append(Paragraph(desc, body_style))

    story.append(PageBreak())
    story.append(Paragraph("The Velorians – Zephyria's Dominant Species", h1_style))
    story.append(Paragraph(
        "The Velorians are the sentient, technologically advanced civilization of Zephyria. Bipedal and bilaterally symmetrical, they share a superficial resemblance to humans but differ significantly in biology, culture, and cognition.",
        body_style))

    velorian_sections = [
        ("Biology", "Velorians stand 1.6–2.1 meters tall, with slender builds and four-fingered hands. Their skin tones range from deep indigo to pale silver, depending on continental origin. They possess four eyes — two forward-facing for depth perception and two lateral for a near-360° field of view. Their auditory range extends into infrasound, allowing them to perceive the planetary rumbles that precede earthquakes. Average lifespan is 180 Zephyrian years (~191 Earth years)."),
        ("Cognition and Communication", "Velorian cognition is characterized by exceptional pattern recognition and distributed memory — they experience memories as vivid, multi-sensory re-livings rather than passive recollections. Their primary language, Veloric, is tonal and partially electromagnetic; Velorians possess bio-electric organs near their temples that transmit emotional nuance alongside spoken words. A Velorian 'conversation' therefore carries layers of meaning inaccessible to external observers."),
        ("Society and Culture", "Velorian society is organized into Resonance Circles — communities of 200–500 individuals bound by shared values rather than family ties. Decision-making is consensus-based, facilitated by dedicated mediators called Harmonists. Art, music, and memory-sharing (direct experience transmission via neural micro-symbiote networks) are the pillars of Velorian cultural life. War has been absent from Zephyria for over 600 Velorian years."),
        ("Technology", "The Velorians achieved spaceflight 300 years ago and have established research stations on all three moons. Their energy infrastructure is entirely renewable — tidal, geothermal, and solar. They have not yet developed faster-than-light travel, making contact with Earth purely observational (via deep-space transmission). Their computing architecture is bio-integrated, using engineered micro-symbiote colonies as living processors."),
    ]
    for name, desc in velorian_sections:
        story.append(Paragraph(name, h2_style))
        story.append(Paragraph(desc, body_style))


# ─────────────────────────────────────────────
# DOC 4: Space Exploration & Cosmic Phenomena
# ─────────────────────────────────────────────
def doc_space_exploration(story):
    story.append(Paragraph("Space Exploration & Cosmic Phenomena", title_style))
    story.append(Paragraph("From Earth Rockets to the Edge of the Observable Universe", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=13, alignment=TA_CENTER, textColor=colors.HexColor('#b71c1c'))))
    story.append(Spacer(1, 0.3*inch))

    sections = [
        ("History of Space Exploration",
         "Humanity's journey into space began on October 4, 1957, when the Soviet Union launched Sputnik 1, the first artificial satellite. Twelve years later, Apollo 11 landed humans on the Moon (July 20, 1969). The Space Shuttle era (1981–2011) demonstrated reusable spacecraft. Today, private companies like SpaceX and Blue Origin are reshaping access to orbit, while international missions target the Moon, Mars, and the outer solar system."),
        ("The James Webb Space Telescope",
         "Launched in December 2021, the James Webb Space Telescope (JWST) is the most powerful space observatory ever built. Observing in infrared, JWST can peer through dust clouds to witness star formation, analyse the atmospheres of exoplanets for biosignatures, and look back to within 200 million years of the Big Bang. Its first images revealed galaxies more mature and massive than theoretical models predicted, prompting revisions to our understanding of early cosmic history."),
        ("Black Holes",
         "Black holes are regions of spacetime where gravity is so intense that nothing — not even light — can escape. They form when massive stars collapse at the end of their lives (stellar black holes), or through other processes producing supermassive black holes millions to billions of times the mass of the Sun. The first direct image of a black hole (M87*) was captured in 2019 by the Event Horizon Telescope. Black holes distort spacetime around them, creating effects like gravitational lensing and time dilation."),
        ("Neutron Stars and Pulsars",
         "When stars between 8 and 20 solar masses explode as supernovae, they can leave behind neutron stars — incredibly dense objects roughly 20 km across but containing more mass than the Sun. A teaspoon of neutron star material weighs approximately a billion tonnes. Pulsars are rapidly rotating neutron stars that emit beams of electromagnetic radiation; as they spin, these beams sweep across Earth like cosmic lighthouses. Millisecond pulsars rotate hundreds of times per second with extraordinary clockwork regularity."),
        ("Gravitational Waves",
         "Predicted by Einstein in 1915 and first directly detected in 2015 by LIGO, gravitational waves are ripples in the fabric of spacetime caused by accelerating massive objects — most dramatically by merging black holes or neutron stars. Detection requires measuring length changes 1,000 times smaller than a proton. Gravitational wave astronomy has opened an entirely new observational window on the Universe, revealing merging compact objects and testing general relativity in extreme conditions."),
        ("The Search for Extraterrestrial Intelligence",
         "SETI (Search for Extraterrestrial Intelligence) has monitored radio frequencies since 1960, searching for signals of technological origin. The discovery of Zephyria's biosignatures in 2087 transformed SETI from a speculative field into a central priority of international science. The Zephyrian Transmission Project (ZTP), begun in 2092, involves beaming mathematical primer sequences toward Lyris-7 — a message that will arrive in approximately 340 years."),
        ("Exoplanet Detection Methods",
         "Astronomers detect exoplanets using several techniques. The Transit Method detects the dimming of a star as a planet crosses in front of it; the Radial Velocity Method measures stellar wobble caused by a planet's gravity; Direct Imaging captures photons from the planet itself (rare and difficult); and Gravitational Microlensing exploits the bending of background starlight by a planet's gravity. Each method has biases — transits favour large close-in planets, microlensing works best for distant systems."),
    ]

    for heading, body in sections:
        story.append(Paragraph(heading, h1_style))
        story.append(Paragraph(body, body_style))
        story.append(Spacer(1, 0.1*inch))


# ─────────────────────────────────────────────
# DOC 5: Zephyria Q&A / FAQ (ideal for RAG)
# ─────────────────────────────────────────────
def doc_zephyria_faq(story):
    story.append(Paragraph("Zephyria & the Universe – Frequently Asked Questions", title_style))
    story.append(Paragraph("A Reference Guide for the Cosmos Voice Assistant", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=13, alignment=TA_CENTER, textColor=colors.HexColor('#e65100'))))
    story.append(Spacer(1, 0.3*inch))

    faqs = [
        ("Where is Planet Zephyria located?",
         "Zephyria orbits in the habitable zone of the binary star system Lyris-7, approximately 340 light-years from Earth in the constellation Aquila. It lies within the Veil Nebula Cluster (VNC-4412)."),
        ("Is Zephyria bigger than Earth?",
         "Yes. Zephyria has a diameter of 14,200 km compared to Earth's 12,742 km, making it about 11% wider. Its mass is 1.3 times Earth's, resulting in a surface gravity of 1.08 g — slightly stronger than Earth's."),
        ("What does Zephyria look like from space?",
         "From space, Zephyria appears as a deep sapphire-blue sphere with swirling white cloud systems. Its three moons are visible in close orbit. At night, the bioluminescent Luminar forests create faint greenish-gold glows visible along the continent of Valdris."),
        ("How long is a Zephyrian year?",
         "A Zephyrian year lasts 387 Earth days. A Zephyrian day is 28 Earth hours long."),
        ("Who are the Velorians?",
         "The Velorians are Zephyria's dominant sentient species — bipedal beings with four eyes, indigo-to-silver skin, and a lifespan of about 180 Zephyrian years. They communicate through a blend of tonal speech and bioelectric emotional signals. Their society has been peaceful for over 600 Zephyrian years."),
        ("What is Zephyria's atmosphere made of?",
         "Zephyria's atmosphere contains 74% nitrogen, 22% oxygen, 2% argon, and trace amounts of carbon dioxide, methane, and water vapour. Its higher oxygen content compared to Earth gives the sky a deeper blue hue."),
        ("What are Luminar Trees?",
         "Luminar Trees are the most iconic plants of Zephyria — bioluminescent giants growing up to 60 metres tall, with leaves that glow violet and gold at night. They photosynthesize using both visible and ultraviolet light."),
        ("What is a Skyweaver?",
         "Skyweavers are six-winged aerial creatures resembling manta rays crossed with jellyfish. They glide at altitudes up to 5,000 metres, filter-feeding on atmospheric spores. With wingspans up to 4 metres, they are considered sacred by the Velorians."),
        ("Have Zephyrians made contact with Earth?",
         "Zephyrian contact has been observational only. Humanity detected their biosignatures in 2087 and began beaming mathematical primer messages toward Lyris-7 in 2092. The signals will not arrive for approximately 340 years."),
        ("How old is the Universe?",
         "The Universe is approximately 13.8 billion years old, dating from the Big Bang — the rapid expansion from an extremely hot, dense initial state."),
        ("What is dark matter?",
         "Dark matter is an invisible substance comprising about 27% of the Universe. It does not interact with light but exerts gravitational influence, holding galaxies together. Its true nature remains one of the biggest unsolved problems in physics."),
        ("What are gravitational waves?",
         "Gravitational waves are ripples in spacetime caused by accelerating massive objects, such as merging black holes. First predicted by Einstein in 1915 and detected in 2015 by LIGO, they represent a new way to observe the Universe."),
        ("How many planets are in our Solar System?",
         "Our Solar System has 8 planets: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. Pluto was reclassified as a dwarf planet in 2006."),
        ("What is a light-year?",
         "A light-year is the distance light travels in one year in a vacuum — approximately 9.46 trillion kilometres (5.88 trillion miles). It is used to express vast astronomical distances."),
        ("What is the Milky Way?",
         "The Milky Way is our home galaxy — a barred spiral galaxy containing 100–400 billion stars, spanning approximately 100,000 light-years. Our Solar System lies about 26,000 light-years from the galactic centre in the Orion Arm."),
        ("What are the three moons of Zephyria called?",
         "Zephyria's three moons are named Aela (the largest), Mira (a medium-sized reddish moon), and Dusk (a small, dark outer moon). Their combined tidal forces drive dramatic ocean currents and stunning aurora displays."),
        ("What energy does Zephyrian civilization use?",
         "The Velorian civilization runs entirely on renewable energy — tidal power from the three moons' gravitational pull, geothermal energy from Zephyria's active core, and solar energy from the binary star system Lyris-7."),
        ("What is the Singing Peaks mountain range?",
         "The Singing Peaks is Zephyria's tallest mountain range, located on the continent of Valdris, rising to 11,000 metres. The range is famous for the haunting, resonant tones produced when wind passes through crystalline rock formations."),
    ]

    for i, (q, a) in enumerate(faqs):
        story.append(Paragraph(f"Q: {q}", h2_style))
        story.append(Paragraph(f"A: {a}", body_style))
        story.append(Spacer(1, 0.1*inch))


# ─────────────────────────────────────────────
# Generate all documents
# ─────────────────────────────────────────────
if __name__ == '__main__':
    make_doc('01_universe_overview.pdf', doc_universe)
    make_doc('02_zephyria_world_guide.pdf', doc_zephyria_overview)
    make_doc('03_zephyria_life_forms.pdf', doc_zephyria_life)
    make_doc('04_space_exploration_phenomena.pdf', doc_space_exploration)
    make_doc('05_zephyria_faq.pdf', doc_zephyria_faq)
    print("\nAll knowledge base PDFs generated successfully!")
