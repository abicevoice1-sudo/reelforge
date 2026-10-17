from pathlib import Path

from reelforge.captions import Word, build_ass, distribute_words
from reelforge.music import duck_expression, speech_segments
from reelforge.schemas import Scene


def test_distribute_words_even():
    scene = Scene(id=1, voiceover="one two three four", on_screen_text="x",
                  stock_query="y", duration=4.0)
    words = distribute_words(scene, 4.0, 10.0)
    assert len(words) == 4
    assert words[0].start == 10.0 and words[-1].end == 14.0


def test_build_ass_karaoke(tmp_path: Path):
    words = [Word("hello", 0.0, 0.5), Word("world", 0.5, 1.0)]
    out = tmp_path / "c.ass"
    build_ass(words, out, style="karaoke")
    text = out.read_text()
    assert "\\kf" in text  # karaoke timing tags
    assert "hello" in text and "world" in text
    assert "PlayResX: 1080" in text


def test_speech_segments_merge():
    words = [Word("a", 0.0, 0.3), Word("b", 0.4, 0.7), Word("c", 5.0, 5.3)]
    segs = speech_segments(words)
    assert len(segs) == 2  # first two merge (gap 0.1 < 0.4)


def test_duck_expression_shape():
    words = [Word("a", 1.0, 2.0)]
    expr = duck_expression(words, 0.12, 0.04)
    assert "between(t,0.85,2.15)" in expr
    assert expr.startswith("if(")
