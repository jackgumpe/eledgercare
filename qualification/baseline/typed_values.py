"""Candidate-only typed lexical conversion. Never accepts an expected answer."""
import datetime
import re
from decimal import Decimal, localcontext
from native import norm

# Frozen from dev schema/printed forms; grouped integers only for USD.
INTEGER=r'(?:0|[1-9][0-9]{0,23})'
GROUPED=r'(?:[1-9][0-9]{0,2}(?:,[0-9]{3}){1,7})'
FRACTION=r'(?:\.[0-9]{1,6})?'
UNITS=('BX','EA','HR','KT','PR')
SUPPORTED={'identifier','text','date_iso','boolean_mark','currency_usd','decimal_2','rate_percent'}

def convert(raw,value_type,slot=None):
    result={'raw':raw,'value_type':value_type,'slot':slot,'status':'missing','canonical':None}
    def finish(status,canonical=None,**extra):return {**result,'status':status,'canonical':canonical,**extra}
    if raw is None:return result
    if not isinstance(raw,str):return finish('unsupported_candidate_structure')
    value=norm(raw)
    if value_type not in SUPPORTED:return finish('unsupported_type')
    if value_type in {'text','identifier'}:return finish('parsed',value)
    if len(value)>128:return finish('lexical_limit')
    if value_type=='boolean_mark':
        return finish('parsed',{'[X]':'true','[ ]':'false'}[value]) if value in ('[X]','[ ]') else finish('invalid_boolean_mark')
    if value_type=='date_iso':
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):return finish('invalid_date_iso')
        try:datetime.date.fromisoformat(value)
        except ValueError:return finish('invalid_date_iso')
        return finish('parsed',value)
    unit=None
    if value_type=='decimal_2' and slot=='qty_unit':
        match=re.fullmatch(r'(.+) ('+'|'.join(UNITS)+r')',value)
        if not match:return finish('invalid_or_unsupported_quantity_unit')
        value,unit=match.groups()
    integer='(?:'+INTEGER+'|'+GROUPED+')' if value_type=='currency_usd' else INTEGER
    prefix=r'-?\$?' if value_type=='currency_usd' else r'-?'
    suffix='%' if value_type=='rate_percent' else ''
    if not re.fullmatch(prefix+integer+FRACTION+suffix,value):return finish('invalid_numeric_grammar')
    with localcontext() as context:
        context.prec=40
        number=Decimal(value.replace('$','').replace(',','').removesuffix('%'))
        if number.is_zero() and number.is_signed():return finish('unsupported_negative_zero')
        places=4 if value_type=='rate_percent' else 2
        if value_type=='rate_percent':number/=100
        quantum=Decimal('0.0001' if places==4 else '0.01');exact=number.quantize(quantum)
        if number!=exact:return finish('non_exact_precision')
        return finish('parsed',format(exact,f'.{places}f'),**({'quantity_unit_observed':unit} if unit else {}))

def compare(raw,metadata,eligible,slot=None):
    parsed=convert(raw,metadata.get('value_type'),slot)
    target=metadata.get('normalized_value')
    # Corpus targets are canonical strings. Unsupported target shape remains counted.
    target_supported=isinstance(target,str)
    exact=parsed['status']=='parsed' and target_supported and parsed['canonical']==norm(target)
    return {**parsed,'expected_normalized':target,'reference_status':'supported' if target_supported else 'unsupported_normalized_target',
            'observed_exact':exact,'credited_exact':bool(exact and eligible)}
