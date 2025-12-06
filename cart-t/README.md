# CAR-T Clinical Trial Data 

This folder contains a synthetic clinical trial dataset provided by [OpenClinica](https://www.openclinica.com/). 

## Study Overview

**Study Name:** CAR-T for ALL  
**Protocol:** CART2020  
**Description:** A Phase IIb, double-blind, multi-center study of CAR-T cell therapy in adults with acute lymphoblastic leukemia.

**File:** [`car-t-openclinica.xml`](car-t-openclinica.xml)  
**Format:** [ODM v1.3](https://www.cdisc.org/standards/data-exchange/odm-xml/odm-xml-v1-3-2)

## Study Sites

The study includes multiple participating sites:
- Dana-Farber Cancer Institute
- Cedars-Sinai
- MGH (Massachusetts General Hospital)
- Abbott
- University Hospital
- Children's National
- St James's University Hospital

## Study Events

The clinical trial protocol includes 23 study events organized across different visit types:

### Unscheduled Events
1. **Informed Consent** - eConsent process
2. **Enrollment** - Eligibility screening and enrollment
3. **Baseline** - Demographics, baseline labs, and randomization
4. **Quality of Life** - QoL assessments (RAND SF-12, EQ-5D-5L surveys)
5. **AE Coding** - MedDRA coding for adverse events
6. **ConMed Coding** - RxNorm coding for concomitant medications
7. **Health History** - Patient health history
8. **Medical History** - Medical history documentation

### Common/Repeating Events
9. **Source Documents**
10. **Labs** - Laboratory results
11. **Medical History/Comorbidities**
12. **Adverse Events**
13. **Concomitant Medications**
14. **Endpoint** - Suspected MI (myocardial infarction) events
15. **Adjudication** - Committee review of endpoints
16. **Disposition**
17. **Misc. Form Capabilities**
18. **Meds from EHR** - Medications from Electronic Health Records
19. **Immunizations from EHR**
20. **Encounters from EHR**
21. **Procedures from EHR**
22. **Labs from EHR**
23. **Conditions from EHR**

## Key Forms (CRFs)

The study includes various Case Report Forms (CRFs):
- **ICF (eConsent)** - Electronic informed consent
- **Eligibility** - Inclusion/exclusion criteria evaluation
- **Demographics and History** - Patient demographics and medication history
- **Baseline Labs and Imaging** - Chemistry panel, nephrology, imaging scans
- **Randomize** - Randomization assignment
- **RAND SF-12 Survey** - Quality of life assessment
- **EQ-5D-5L Questionnaire** - Health status questionnaire
- **Skin Conditions Questionnaire**
- **Adverse Event** - AE reporting with MedDRA coding
- **ConMed** - Concomitant medications with RxNorm coding
- **Suspected MI** - Endpoint evaluation
- **Evaluator A/B** - Independent adjudication
- **Committee Review** - Final adjudication
- **Disposition** - Study disposition tracking

## Data Standards

The XML file follows CDISC ODM v1.3 standards with OpenClinica extensions:
- **Coding Systems:**
  - MedDRA for adverse event coding
  - RxNorm for medication coding
- **Standards Compliance:**
  - CDISC ODM 1.3
  - OpenClinica ODM extensions v3.1

## File Structure

The ODM XML contains:
- Study metadata and protocol definition
- Form and item group definitions
- Code lists and controlled terminology
- Clinical data for all subjects
- Audit trail information
