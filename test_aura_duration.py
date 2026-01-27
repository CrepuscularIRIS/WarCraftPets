from engine.resolver.aura_manager import AuraManager


def test_aura_duration_no_tickdown_first_round() -> None:
    am = AuraManager()
    ar = am.apply(
        owner_pet_id=1,
        caster_pet_id=1,
        aura_id=10,
        duration=1,
        tickdown_first_round=False,
        source_effect_id=99,
    )
    assert ar.aura is not None
    assert ar.aura.remaining_duration == 1

    expired = am.tick(1)
    assert expired == []
    assert am.get(1, 10) is not None
    assert am.get(1, 10).remaining_duration == 1

    expired = am.tick(1)
    assert len(expired) == 1
    assert am.get(1, 10) is None


def test_aura_duration_tickdown_first_round() -> None:
    am = AuraManager()
    ar = am.apply(
        owner_pet_id=1,
        caster_pet_id=1,
        aura_id=11,
        duration=1,
        tickdown_first_round=True,
        source_effect_id=99,
    )
    assert ar.aura is not None
    assert ar.aura.remaining_duration == 1

    expired = am.tick(1)
    assert len(expired) == 1
    assert am.get(1, 11) is None


def test_aura_duration_tickdown_first_round_longer() -> None:
    am = AuraManager()
    ar = am.apply(
        owner_pet_id=1,
        caster_pet_id=1,
        aura_id=12,
        duration=2,
        tickdown_first_round=True,
        source_effect_id=99,
    )
    assert ar.aura is not None
    assert ar.aura.remaining_duration == 2

    expired = am.tick(1)
    assert expired == []
    assert am.get(1, 12) is not None
    assert am.get(1, 12).remaining_duration == 1

    expired = am.tick(1)
    assert len(expired) == 1
    assert am.get(1, 12) is None
