import asyncio

import pytest

from app.autonomy.task_relation import classify_task, local_relation, parse_task_control


TAJ = 'create tajmahal in blender'


@pytest.mark.parametrize('text', [
    'add details to it', 'create a dome on it', 'make dome larger',
    'Create Taj Mahal in Blender!', 'CREATE TAJ-MAHAL IN BLENDER.',
    'please create Taj Mahal', 'Make Taj Mahal more detailed',
    'move the tower to the right', 'render the scene', 'retry', 'keep going',
    'isko bada karo', 'dome bada karo', 'aur details add karo', 'इसे बड़ा करो',
    '/update create a sports car',
])
def test_clear_followups_stay_in_current_project(text):
    assert local_relation(text, TAJ) == 'related'


@pytest.mark.parametrize('text', [
    'create a sports car in Blender', 'please create a 3D robot',
    'create a car and paint it red', 'make sports car realistic',
    'make red sports car',
    'I want to build a city in Blender', 'could you model a chair',
    'new project: Taj Mahal', 'make a fresh scene with Taj Mahal',
    'start over with Taj Mahal', 'naya project banao', 'नया प्रोजेक्ट बनाओ',
    '/new make dome larger', '/NEW: Taj Mahal',
])
def test_unrelated_creation_and_explicit_new_do_not_edit_old_project(text):
    assert local_relation(text, TAJ) == 'new'


@pytest.mark.parametrize(('text', 'current'), [
    ('create a sports car in Blender', 'create a realistic Taj Mahal model in Blender'),
    ('Create a big village with high quality graphics', 'create a big detailed robot'),
    ('build a chair', 'build a city'),
])
def test_shared_generic_words_do_not_connect_unrelated_subjects(text, current):
    assert local_relation(text, current) == 'new'


@pytest.mark.parametrize('text', ['', '/new', '/update', 'a sports car',
    'Taj Mahal and a city', 'what about a temple'])
def test_ambiguous_requests_need_classification_or_explicit_control(text):
    assert local_relation(text, TAJ) == 'uncertain'


def test_explicit_controls_and_existing_object_names():
    assert parse_task_control(' /NEW  create a city ') == ('new', 'create a city')
    assert parse_task_control('/update: rotate dome') == ('related', 'rotate dome')
    assert parse_task_control('/newspaper') == (None, '/newspaper')
    assert local_relation('MainDome larger', TAJ, ['MainDome']) == 'related'
    assert local_relation('MainDome', TAJ, ['MainDome']) == 'uncertain'
    assert local_relation('MainDome2 larger', TAJ, ['MainDome']) == 'uncertain'
    assert local_relation('create anything', '') == 'new'
    assert local_relation('/update move dome', '') == 'uncertain'


@pytest.mark.asyncio
async def test_clear_intent_does_not_request_another_chat():
    async def forbidden(*args, **kwargs):
        raise AssertionError('Clear intent should not call the provider')
    assert await classify_task(forbidden, 'make dome larger', TAJ) == 'related'
    assert await classify_task(forbidden, 'create a sports car in Blender', TAJ) == 'new'
    assert await classify_task(forbidden, '/new', TAJ) == 'uncertain'


@pytest.mark.asyncio
async def test_ambiguous_intent_uses_injected_request_and_bounded_validation():
    prompts = []
    async def request(prompt, validate, fallback):
        prompts.append(prompt)
        for response in ({'relation': 'update'}, {'relation': []}, {}, 'related'):
            with pytest.raises(ValueError):
                validate(response)
        assert fallback() == 'uncertain'
        return validate({'relation': 'new'})
    assert await classify_task(request, 'what about a temple', TAJ,
        [dict(name='Dome', type='MESH')]) == 'new'
    assert len(prompts) == 1
    assert 'Dome' in prompts[0] and 'what about a temple' in prompts[0]


@pytest.mark.asyncio
async def test_provider_failure_and_invalid_fallback_remain_uncertain():
    async def failed(*args, **kwargs):
        raise RuntimeError('Provider unavailable')
    async def invalid(*args, **kwargs):
        return {'relation': 'related'}
    async def slow(*args, **kwargs):
        await asyncio.sleep(10)
    for request in (failed, invalid, slow):
        assert await classify_task(request, 'what about a temple', TAJ,
            timeout=.01) == 'uncertain'


@pytest.mark.asyncio
async def test_permission_denial_is_not_swallowed():
    async def denied(*args, **kwargs):
        raise PermissionError('Denied')
    with pytest.raises(PermissionError):
        await classify_task(denied, 'what about a temple', TAJ)
