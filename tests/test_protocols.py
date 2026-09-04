from eval.protocols import parse_asvspoof_protocol, parse_in_the_wild_protocol, subsample_trials


def test_parse_asvspoof_protocol(tmp_path):
    protocol = tmp_path / "protocol.txt"
    protocol.write_text(
        "LA_0001 LA_E_0001 - A11 spoof\n"
        "LA_0002 LA_E_0002 - - bonafide\n"
    )
    trials = parse_asvspoof_protocol(str(protocol), str(tmp_path / "flac"), ext=".flac")
    assert len(trials) == 2
    assert trials[0].label == "spoof"
    assert trials[0].audio_path.endswith("LA_E_0001.flac")
    assert trials[1].label == "bonafide"


def test_parse_asvspoof_protocol_filters_by_subset(tmp_path):
    protocol = tmp_path / "trial_metadata.txt"
    protocol.write_text(
        "LA_0023 DF_E_0001 nocodec asvspoof A14 spoof notrim progress traditional_vocoder - - - -\n"
        "TEF2 DF_E_0002 low_m4a vcc2020 Task1 spoof notrim eval neural_vocoder - - - -\n"
        "VCC2TM2 DF_E_0003 mp3m4a vcc2018 - bonafide notrim eval bonafide - - - -\n"
    )
    trials = parse_asvspoof_protocol(str(protocol), str(tmp_path / "flac"), required_subset="eval")
    assert len(trials) == 2
    assert all("DF_E_0001" not in t.audio_path for t in trials)


def test_parse_in_the_wild_protocol(tmp_path):
    meta = tmp_path / "meta.csv"
    meta.write_text("file,speaker,label\n0.wav,Alice,spoof\n1.wav,Bob,bona-fide\n")
    trials = parse_in_the_wild_protocol(str(meta), str(tmp_path))
    assert len(trials) == 2
    assert trials[0].label == "spoof"
    assert trials[1].label == "bonafide"


def test_subsample_trials_preserves_ratio_roughly(tmp_path):
    from eval.protocols import Trial

    trials = [Trial(f"{i}.flac", "spoof") for i in range(80)] + [Trial(f"b{i}.flac", "bonafide") for i in range(20)]
    sub = subsample_trials(trials, n=20, seed=0)
    n_spoof = sum(1 for t in sub if t.label == "spoof")
    n_bonafide = sum(1 for t in sub if t.label == "bonafide")
    assert n_spoof + n_bonafide == len(sub)
    assert 12 <= n_spoof <= 20  # roughly 80% of the subsample
    assert n_bonafide >= 1
