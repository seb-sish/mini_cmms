"""Статические проверки контракта; API, ARQ и БД не запускаются.

uv run --no-project --with pyyaml --with 'jsonschema[format]' \
    --with openapi-spec-validator python Mini_CMMS_API_Validation.py
"""
from __future__ import annotations

import csv
import re
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

HERE = Path(__file__).resolve().parent
ERRORS: list[str] = []
COUNTS = dict(examples=0, parameters_and_headers=0, negative_probes=0, flow_steps=0)


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        if len(keys) != len(set(keys)):
            raise ValueError(f'Повторён YAML-ключ, строка {node.start_mark.line + 1}')
        return super().construct_mapping(node, deep=deep)


def load(name):
    return yaml.load((HERE / name).read_text(encoding='utf-8'), Loader=UniqueKeyLoader)


def require(condition, message):
    if not condition:
        ERRORS.append(message)


spec = load('Mini_CMMS_OpenAPI_3.1.1.yaml')
validate_spec(spec)
checker = FormatChecker()
for name in ('date', 'date-time', 'uuid', 'uri-reference'):
    if name not in checker.checkers:
        raise SystemExit(f'Нет проверки {name}; установите jsonschema[format], см. команду в начале файла')


def check(value, schema, where, expected_valid=True):
    # Корень с components разрешает локальные ссылки без deprecated RefResolver.
    wrapped = {'allOf': [schema], 'components': spec['components']}
    issues = list(Draft202012Validator(wrapped, format_checker=checker).iter_errors(value))
    if expected_valid:
        ERRORS.extend(f'{where}: {list(e.absolute_path)}: {e.message}' for e in issues)
    else:
        COUNTS['negative_probes'] += 1
        require(bool(issues), f'{where}: запрещённое значение прошло схему')


for name, schema in spec['components']['schemas'].items():
    Draft202012Validator.check_schema(schema)
require(spec['openapi'] == '3.1.1', 'Версия OAS должна быть 3.1.1')
require(spec['servers'][0]['url'] == '/api/v1', 'Неверный base path')
operations, cases = {}, {}
CSV_HEADERS = ['ID', 'Метод', 'Путь', 'operationId', 'Сценарий', 'Входные данные / предусловие',
               'Ожидаемый HTTP статус', 'Код ошибки', 'Ожидаемый результат']


def collect(c, method, path, oid):
    require(c['id'] not in cases, 'Повторён ID ' + c['id'])
    status = '' if c['expected_http_status'] is None else str(c['expected_http_status'])
    cases[c['id']] = [c['id'], method.upper(), path, oid, c['case'], c['request_or_state'],
                      status, c.get('expected_error_code') or '', c['expected_effect']]


for path, item in spec['paths'].items():
    for method, operation in item.items():
        oid = operation['operationId']
        require(oid not in operations, 'Повторён operationId ' + oid)
        operations[oid] = (method, path, operation)
        params = operation.get('parameters', [])
        require({p['name'] for p in params if p['in'] == 'path'} == set(re.findall(r'\{([^}]+)\}', path)), oid + ': path parameters')
        require(len({(p['in'], p['name']) for p in params}) == len(params), oid + ': повторён параметр')
        require('x-allowed-roles' in operation and 'x-object-visibility' in operation, oid + ': нет матрицы доступа')
        for p in params:
            if p['in'] == 'path':
                require(p.get('required') is True, oid + ': path parameter необязателен')
            if 'example' in p:
                check(p['example'], p['schema'], oid + ': parameter ' + p['name'])
                COUNTS['parameters_and_headers'] += 1
        if method == 'patch':
            require(any(p['in'] == 'header' and p['name'] == 'If-Match' and p.get('required') for p in params), oid + ': If-Match')
            require({'412', '428'} <= operation['responses'].keys(), oid + ': precondition responses')
        payloads = [('request', operation.get('requestBody'))]
        payloads += [('response ' + status, response) for status, response in operation['responses'].items()]
        for label, payload in payloads:
            if not payload:
                continue
            for header, definition in payload.get('headers', {}).items():
                if 'example' in definition:
                    check(definition['example'], definition['schema'], oid + ': header ' + header)
                    COUNTS['parameters_and_headers'] += 1
            for media, content in payload.get('content', {}).items():
                require(bool(content.get('examples')), oid + ': нет примера ' + label)
                for name, example in content.get('examples', {}).items():
                    COUNTS['examples'] += 1
                    check(example['value'], content['schema'], f'{oid}: {label}: {name}')
                    if media == 'application/problem+json' and label.startswith('response '):
                        require(example['value']['status'] == int(label.split()[1]), oid + ': status не совпадает с HTTP')
        for status, response in operation['responses'].items():
            require(status != '204' or not response.get('content'), oid + ': тело при 204')
            if status in ('201', '401'):
                header = {'201': 'Location', '401': 'WWW-Authenticate'}[status]
                require(header in response.get('headers', {}), oid + ': нет ' + header)
        require(any(200 <= c['expected_http_status'] < 300 for c in operation['x-corner-cases']), oid + ': нет успешного теста')
        for c in operation['x-corner-cases']:
            status = str(c['expected_http_status'])
            require(status in operation['responses'], c['id'] + ': HTTP не объявлен')
            if c.get('expected_error_code') and status in operation['responses']:
                value = dict(type='about:blank', title='Ошибка', status=int(status), detail='Тест', code=c['expected_error_code'])
                check(value, operation['responses'][status]['content']['application/problem+json']['schema'], c['id'] + ': code')
            collect(c, method, path, oid)

for c in spec.get('x-protocol-test-cases', []):
    status = c['expected_http_status']
    require(status == 405 or (status is None and c.get('expected_transport_error')), c['id'] + ': протокольный статус')
    if status == 405:
        require(c['path'] in spec['paths'] and c['method'].lower() not in spec['paths'][c['path']], c['id'] + ': метод существует')
        require(c.get('expected_error_code') == 'METHOD_NOT_ALLOWED', c['id'] + ': неверный код 405')
        allowed = {method.upper() for method in spec['paths'].get(c['path'], {})}
        header = c.get('expected_headers', {}).get('Allow', '')
        require({method.strip() for method in header.split(',')} == allowed, c['id'] + ': неверный Allow')
        require(c.get('expected_state_unchanged') is True, c['id'] + ': не проверена неизменность данных')
    elif status is None:
        require(c.get('expected_transport_error') == 'CONNECTION_FAILED', c['id'] + ': неизвестный транспортный код')
        require(c.get('expected_error_code') is None and not c.get('expected_headers'), c['id'] + ': транспортный отказ содержит HTTP-ответ')
    collect(c, c['method'], c['path'], '')
with (HERE / 'Mini_CMMS_API_Test_Cases.csv').open(encoding='utf-8-sig', newline='') as stream:
    reader = csv.reader(stream)
    require(next(reader) == CSV_HEADERS, 'CSV: неверные заголовки')
    rows = list(reader)
require(len(rows) == len({row[0] for row in rows}), 'CSV: повторён ID')
require({row[0] for row in rows} == set(cases), 'CSV/YAML: различаются ID')
for row in rows:
    require(cases.get(row[0]) == row, 'CSV/YAML: отличается содержимое ' + row[0])

for name, value in [('date-time', 'not-a-date'), ('date-time', '2026-02-30T00:00:00Z'),
                    ('uuid', 'not-a-uuid'), ('uri-reference', 'not a URI')]:
    check(value, {'type': 'string', 'format': name}, 'format probe ' + name, False)
check('2026-10-23T12:00:00+03:00', {'type': 'string', 'format': 'date-time', 'pattern': 'Z$'}, 'UTC-only', False)
for name in ('UserPatch', 'EquipmentPatch', 'FaultPatch', 'MaintenancePlanPatch', 'WorkOrderPatch'):
    for value in ({}, {'unexpected_field': 1}):
        check(value, {'$ref': '#/components/schemas/' + name}, name + ' negative', False)
closed = deepcopy(next(iter(spec['paths']['/work-orders/{work_order_id}/close']['post']['responses']['200']['content']['application/json']['examples'].values()))['value'])
for key, value in [('result', None), ('completed_at', None), ('closed_at', None), ('status', 'CREATED')]:
    check(dict(closed, **{key: value}), {'$ref': '#/components/schemas/WorkOrder'}, 'WorkOrder invariant ' + key, False)
check({'reason': '   '}, {'$ref': '#/components/schemas/CancelWorkOrderRequest'}, 'blank reason', False)
plan = deepcopy(next(iter(spec['paths']['/maintenance-plans']['post']['responses']['201']['content']['application/json']['examples'].values()))['value'])
plan.update(scope='EQUIPMENT',equipment_id=None)
check(plan, {'$ref': '#/components/schemas/MaintenancePlan'}, 'invalid plan scope', False)
broken = dict(closed,type='REPAIR',schedule_id='11111111-aaaa-4111-8111-111111111111')
check(broken, {'$ref': '#/components/schemas/WorkOrder'}, 'REPAIR schedule', False)
check(dict(type='about:blank',title='Ошибка',status=400,detail='Тест',code='TEST',instance=None),
      {'$ref': '#/components/schemas/ProblemDetail'}, 'null instance', False)
point = dict(id='11111111-aaaa-4111-8111-111111111111',title='Масло',required=True,order=0,
             checked=False,comment=None,checked_at='2026-10-23T09:00:00Z')
check(point, {'$ref': '#/components/schemas/WorkChecklistItem'}, 'unchecked timestamp', False)

examples = load('Mini_CMMS_API_Examples.yaml')
for flow in examples['flows']:
    clocks = [datetime.fromisoformat(s['clock_utc'].replace('Z', '+00:00')) for s in flow['steps']]
    require(clocks == sorted(clocks), flow['id'] + ': время шагов идёт назад')
    expiries = {r: clocks[0] + timedelta(hours=12) for r in ('admin', 'engineer', 'technician', 'operator')}
    for key, schema_name in [('users', 'User'), ('equipment', 'Equipment'), ('faults', 'Fault')]:
        for record in flow['initial_state'].get(key, []):
            check(record, {'$ref': '#/components/schemas/' + schema_name}, flow['id'] + ': initial ' + key)
            for field in ('created_at', 'updated_at'):
                if field in record:
                    require(datetime.fromisoformat(record[field].replace('Z', '+00:00')) <= clocks[0], flow['id'] + ': fixture из будущего')
    for step in flow['steps']:
        method, path, operation = operations[step['operationId']]
        require(step['method'].lower() == method and step['path_template'] == path, flow['id'] + ': маршрут шага')
        security = operation.get('security', spec.get('security', []))
        if security:
            require(any('BearerAuth' in rule for rule in security), flow['id'] + ': неподдерживаемая security requirement')
            if step['actor'] == 'anonymous':
                require(step['expected_status'] == 401 and not step['headers'].get('Authorization'), flow['id'] + ': анонимный доступ к защищённой операции')
            else:
                expected = 'Bearer ${session.' + step['actor'] + '}'
                require(step['headers'].get('Authorization') == expected, flow['id'] + ': Bearer не соответствует actor')
                if step['expected_status'] == 401:
                    reason = step.get('expected_auth_failure')
                    require(reason in ('REVOKED', 'EXPIRED'), flow['id'] + ': не задана причина отказа сессии')
                    now = datetime.fromisoformat(step['clock_utc'].replace('Z', '+00:00'))
                    if reason == 'REVOKED':
                        require(now < expiries[step['actor']], flow['id'] + ': проверка отзыва маскируется истечением сессии')
                    elif reason == 'EXPIRED':
                        require(now >= expiries[step['actor']], flow['id'] + ': токен ещё не истёк')
        if step['actor'] != 'anonymous' and step['expected_status'] < 400:
            require(step['actor'].upper() in operation['x-allowed-roles'], flow['id'] + ': запрещённая роль в успешном примере')
            require(datetime.fromisoformat(step['clock_utc'].replace('Z', '+00:00')) < expiries[step['actor']], flow['id'] + ': сессия истекла до шага')
        for p in operation.get('parameters', []):
            values = step.get({'path': 'path_params', 'header': 'headers', 'query': 'query'}[p['in']], {})
            if p.get('required'):
                require(p['name'] in values, flow['id'] + ': отсутствует ' + p['name'])
            if p['name'] in values:
                check(values[p['name']], p['schema'], flow['id'] + ': parameter ' + p['name'])
        if operation.get('requestBody'):
            check(step['body'], operation['requestBody']['content']['application/json']['schema'], flow['id'] + ': request')
        response = operation['responses'][str(step['expected_status'])]
        if response.get('content'):
            media = 'application/problem+json' if step['expected_status'] >= 400 else 'application/json'
            check(step['expected_body'], response['content'][media]['schema'], flow['id'] + ': response')
        for name, value in step.get('expected_headers', {}).items():
            require(name in response.get('headers', {}), flow['id'] + ': заголовок не объявлен ' + name)
            if name in response.get('headers', {}):
                check(value, response['headers'][name]['schema'], flow['id'] + ': response header ' + name)
        if step['operationId'] == 'login' and step['expected_status'] == 200:
            token = step['expected_body']
            role = token['user']['role'].lower()
            expiries[role] = datetime.fromisoformat(token['expires_at'].replace('Z', '+00:00'))
            issued = datetime.fromisoformat(step['clock_utc'].replace('Z', '+00:00'))
            require(expiries[role] == issued + timedelta(hours=12), flow['id'] + ': срок токена не 12 часов')
        COUNTS['flow_steps'] += 1
for probe in examples['date_probes']:
    result = date.fromisoformat(probe['completed_on']) + timedelta(days=probe['interval_days'])
    require((result > date.fromisoformat(probe['planned_due_on'])) == probe['allowed'], 'date probe: ' + probe['id'])
    require(str(result) == probe['computed_next_due_on'], 'date result: ' + probe['id'])

print('Paths:', len(spec['paths']), 'Operations:', len(operations), 'Schemas:', len(spec['components']['schemas']))
print('Validated:', COUNTS, 'Cases:', len(cases), 'Flows:', len(examples['flows']))
print('Errors:', len(ERRORS))
for error in ERRORS:
    print('-', error)
if ERRORS:
    raise SystemExit(1)
print('PASS: OAS, форматы, примеры, инварианты схем, CSV и сквозные примеры; runtime не проверялся')
