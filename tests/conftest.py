"""Shared test fixtures for rime-phah-taibun tests."""

import pytest


@pytest.fixture
def itaigi_csv_content():
    """Sample iTaigi CSV content (UTF-8 with BOM simulation)."""
    return (
        '\ufeff"DictWordID","PojUnicode","PojInput","KipUnicode","KipInput",'
        '"HanLoTaibunPoj","HanLoTaibunKip","HoaBun","DataProvidedBy"\n'
        '"1","siān-neh","sian7-neh","siān-neh","sian7-neh",'
        '"𤺪呢","𤺪呢","討厭","Liz Lin"\n'
        '"2","sú-sū","su2-su7","sú-sū","su2-su7",'
        '"死侍","死侍","死侍","Liz Lin"\n'
        '"4","tōa-lâng chhōa gín-á khì chhit-thô",'
        '"toa7-lang5 chhoa7 gin2-a2 khi3 chhit-tho5",'
        '"tuā-lâng tshuā gín-á khì tshit-thô",'
        '"tua7-lang5 tshua7 gin2-a2 khi3 tshit-tho5",'
        '"大人𤆬囡仔去𨑨迌","大人𤆬囡仔去𨑨迌","大人帶小孩去玩耍","葉怡萱"\n'
    )


@pytest.fixture
def taihoa_csv_content():
    """Sample 台華線頂 CSV content."""
    return (
        '\ufeff"DictWordID","PojUnicode","PojUnicodeOthers","PojInput","PojInputOthers",'
        '"HanLoTaibunPoj","KipUnicode","KipUnicodeOthers","KipInput","KipInputOthers",'
        '"HanLoTaibunKip","HoaBun"\n'
        '"1","á-bô","","a2-bo5","","á無","á-bô","","a2-bo5","","á無","不然"\n'
        '"5","à-lêng","","a3-leng5","","啞鈴","à-lîng","","a3-ling5","","啞鈴","小鎮"\n'
        '"6","ā-hó","","a7-ho2","","ā好","ā-hó","","a7-ho2","","ā好","怎好"\n'
    )


@pytest.fixture
def kip_with_alternates_csv():
    """CSV with (替) markers and slash-separated variants."""
    return (
        '\ufeff"DictWordID","PojUnicode","PojUnicodeOthers","PojInput","PojInputOthers",'
        '"HanLoTaibunPoj","KipUnicode","KipUnicodeOthers","KipInput","KipInputOthers",'
        '"HanLoTaibunKip","HoaBun"\n'
        '"100","chi̍t(替)","it","chit8(替)","it",'
        '"一","tsi̍t(替)","it","tsit8(替)","it","一","一"\n'
        '"200","chia̍h/si̍t","","chiah8/sit8","","食","tsia̍h/si̍t","","tsiah8/sit8","","食","吃"\n'
        '"300","kóng--ê","","kong2--e5","","講--ê","kóng--ê","","kong2--e5","","講--ê","所說的"\n'
    )
