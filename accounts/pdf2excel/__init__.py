# accounts/pdf2excel/__init__.py

from . import (
    m_axis_1,
    m_bob_1,
    m_bom_1,
    m_hdfc_1,
    m_icici_1,
    m_sarvodaya_1,
    m_spcb_1,
    m_spcb_2,
    m_sutex_1,
    m_sbi_1,
    m_canara_1,   # <-- use the _1 module
    m_union_1,
    m_pnb_1,
    m_indian_1,
    m_sbi_2,  # <-- new module added here
    m_kalupur_1,
    m_kotak_1,
    m_idbi_choicepoint,
    m_spcb_3,
    m_bandhan_1,
    m_icici_2,
    m_kotak_2,
    m_sbi_3,
)

bank_modules = {
    "axis_1": m_axis_1.axis_1,
    "bob_1": m_bob_1.bob_1,
    "bom_1": m_bom_1.bom_1,
    "hdfc_1": m_hdfc_1.hdfc_1,
    "icici_1": m_icici_1.icici_1,
    "sarvodaya_1": m_sarvodaya_1.sarvodaya_1,
    "spcb_1": m_spcb_1.spcb_1,
    "spcb_2": m_spcb_2.spcb_2,
    "sutex_1": m_sutex_1.sutex_1,
    "sbi_1": m_sbi_1.sbi_1,   # <-- must exist
     "canara_1": m_canara_1.canara_1,
   # <-- point here # now exists ✅
    "union_1": m_union_1.union_1,
    "pnb_1": m_pnb_1.pnb_1, 
    "indian_1": m_indian_1.indian_1,
    "sbi_2": m_sbi_2.sbi_2,  #
    "kalupur_1": m_kalupur_1.kalupur_1,
    "kotak_1" : m_kotak_1.kotak_1,
    "idbi_choicepoint": m_idbi_choicepoint.idbi_choicepoint,
    "spcb_3": m_spcb_3.spcb_3,
    "bandhan_1": m_bandhan_1.bandhan_1,
    "icici_2": m_icici_2.icici_2,
    "kotak_2" : m_kotak_2.kotak_2,
    "sbi_3": m_sbi_3.sbi_3,

}   
