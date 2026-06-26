"""Tests for scriptkit.text — human-friendly formatting."""

import scriptkit.text as text


def test_human_size_binary():
    assert text.human_size(0) == "0 B"
    assert text.human_size(512) == "512 B"
    assert text.human_size(1024) == "1.0 KB"
    assert text.human_size(1536) == "1.5 KB"
    assert text.human_size(5 * 1024**3) == "5.0 GB"


def test_human_size_si():
    assert text.human_size(1000, binary=False) == "1.0 KB"


def test_human_duration():
    assert text.human_duration(0.5) == "500ms"
    assert text.human_duration(4.2) == "4.2s"
    assert text.human_duration(185) == "3m 5s"
    assert text.human_duration(3725) == "1h 2m"


def test_format_timecode():
    assert text.format_timecode(75.5) == "1:15.50"
    assert text.format_timecode(3725.25) == "1:02:05.25"
    assert text.format_timecode(0) == "0:00.00"


def test_human_count():
    assert text.human_count(1, "host") == "1 host"
    assert text.human_count(0, "host") == "0 hosts"
    assert text.human_count(2, "host") == "2 hosts"
    assert text.human_count(2, "entry", "entries") == "2 entries"


def test_truncate():
    assert text.truncate("hello", 10) == "hello"
    assert text.truncate("hello world", 8) == "hello w…"
    assert text.truncate("hello", 5) == "hello"
    assert text.truncate("abc", 2) == "a…"  # one content char + ellipsis
    assert text.truncate("abc", 1) == "a"  # width <= ellipsis length: hard cut
    assert text.truncate("abc", 0) == "abc"
