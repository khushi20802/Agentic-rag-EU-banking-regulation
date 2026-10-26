# Grading sheet

For each question, compare the answer with the key points and enter a score in `eval/grades.json`: **1** = all key points correct, **0.5** = partly correct or incomplete, **0** = wrong or invented. For `not_in_corpus` questions: 1 = clearly says the information is not available (and does not invent it).

## C1 (catalogue): Which AML documents were issued after 2022?

**Key points:**
- EBA/GL/2024/01 (16 Jan 2024)
- AuA GwG (July 2025)
- no other AML documents after 2022

**Tools:** ['query_documents'] | **cited docs:** ['bafin_aua_gwg', 'eba_gl_2024_01'] | **expected docs:** ['eba_gl_2024_01', 'bafin_aua_gwg']

**Answer:**

The AML-related documents in the corpus that were issued after 2022 are:

| Document ID | Reference | Title (English/German) | Issuer | Date |
|-------------|-----------|------------------------|--------|------|
| eba_gl_2024_01 | EBA/GL/2024/01 | **Guidelines amending the ML/TF Risk Factors Guidelines** | European Banking Authority (EBA) | 16 January 2024[1] |
| bafin_aua_gwg | AuA GwG | **Auslegungs- und Anwendungshinweise zum Geldwäschegesetz** | Bundesanstalt für Finanzdienstleistungsaufsicht (BaFin) | 1 July 2025[2] |

These are the only AML-topic documents in the catalogue with a publication date later than 31 December 2022.

---

## C2 (catalogue): Which document amends the EBA ML/TF Risk Factors Guidelines (EBA/GL/2021/02), and when was it issued?

**Key points:**
- EBA/GL/2024/01
- issued 16 January 2024

**Tools:** ['query_documents'] | **cited docs:** ['eba_gl_2024_01'] | **expected docs:** ['eba_gl_2024_01']

**Answer:**

The document that amends the EBA ML/TF Risk Factors Guidelines (EBA/GL/2021/02) is **EBA Guidelines amending the ML/TF Risk Factors Guidelines (EBA/GL/2024/01)**, which was issued on **16 January 2024**[1].

---

## C3 (catalogue): Which documents in the corpus are in German, and who issued them?

**Key points:**
- MaRisk (Rundschreiben 06/2026)
- AuA GwG
- Rundschreiben 14/2026
- all issued by BaFin

**Tools:** ['query_documents'] | **cited docs:** ['bafin_aua_gwg'] | **expected docs:** ['bafin_rs_06_2026', 'bafin_aua_gwg', 'bafin_rs_14_2026']

**Answer:**

The German-language documents in the corpus are:

| Document ID | Title (German) | Issuer |
|-------------|----------------|--------|
| bafin_aua_gwg | Auslegungs- und Anwendungshinweise zum Geldwäschegesetz | BaFin |
| bafin_rs_06_2026 | Mindestanforderungen an das Risikomanagement (MaRisk) | BaFin |
| bafin_rs_14_2026 | Leitlinien zur Festlegung der Kriterien für die Ermittlung der Tätigkeiten gemäß Art. 4 Abs. 1 Nr. 18 CRR | BaFin |

These three documents are all issued by BaFin and are in German[1].

**Reflection flags:**
- unsupported: Document ID bafin_rs_06_2026 is titled "Mindestanforderungen an das Risikomanagement (MaRisk)". (Source does not mention this document or its title.)
- unsupported: Document ID bafin_rs_06_2026 is issued by BaFin. (Source provides no information about this document's issuer.)
- unsupported: Document ID bafin_rs_06_2026 is in German. (Source does not state the language of this document.)
- unsupported: Document ID bafin_rs_14_2026 is titled "Leitlinien zur Festlegung der Kriterien für die Ermittlung der Tätigkeiten gemäß Art. 4 Abs. 1 Nr. 18 CRR". (Source does not mention this document or its title.)
- unsupported: Document ID bafin_rs_14_2026 is issued by BaFin. (Source provides no information about this document's issuer.)
- partially_supported: All three documents are issued by BaFin. (Source confirms BaFin as issuer for AuA GwG but not for the other two documents.)

---

## D1 (content): What should firms check when onboarding customers remotely by video?

**Key points:**
- adequate video/audio quality and lighting
- capture at the moment of verification
- liveness detection
- trained staff / interview guide for attended solutions
- stop the process on technical problems

**Tools:** ['search_documents'] | **cited docs:** ['eba_gl_2022_15'] | **expected docs:** ['eba_gl_2022_15']

**Answer:**

**Checks firms should carry out when onboarding customers remotely by video**

* **Quality of the video/audio feed** – The image and sound must be clear enough to allow an unambiguous verification of the customer’s identity and must be captured in a readable format[2].  

* **Adequate lighting and timing** – Photographs or video recordings must be taken under sufficient lighting and at the moment the customer is performing the verification[3].  

* **Liveness detection** – The solution should include liveness-detection checks (e.g., requiring the customer to perform a specific action or analysing the data automatically) to confirm that a real person is present[3].  

* **Use of reliable technology** – Strong, reliable algorithms and robust technological systems must be employed for identity verification[3].  

* **Up-to-date and sufficient information** – The data collected through the remote solution must be current and adequate to meet the applicable AML/CFT and customer-due-diligence requirements[2].  

* **Employee involvement (attended solutions)**  
  * An employee with sufficient knowledge of AML/CFT rules and security aspects must participate in the verification and be trained to detect and prevent deception techniques[1].  
  * An interview guide defining the steps of the remote verification process and the employee’s actions should be developed[1].  

* **Technical reliability** – The onboarding process must be stopped if technical shortcomings or unexpected connection interruptions are detected, and the process should be restarted or redirected to a face-to-face verification when evidence quality is insufficient[2][4].  

---

## D2 (content): What information should institutions collect to assess the creditworthiness of a consumer borrower?

**Key points:**
- institutions need sufficient, accurate and up-to-date information before concluding a loan agreement (para 84)
- information must be supported by necessary and appropriate evidence, covering at least a defined list of items, starting with the purpose of the loan (para 85)

**Tools:** ['query_documents', 'search_documents'] | **cited docs:** ['eba_gl_2020_06'] | **expected docs:** ['eba_gl_2020_06']

**Answer:**

Institutions should collect, and be able to use, evidence-based information on at least the following items when assessing a consumer borrower’s creditworthiness:

1. **Purpose of the loan** (when relevant to the product)[2]  
2. **Employment details** – type, sector, status (full-time, part-time, contractor, self-employed) and duration[2]  
3. **Source of repayment capacity** (e.g., income, bonuses, commissions, overtime)[2]  
4. **Household composition and dependents**[2]  
5. **Financial commitments and expenses for servicing the loan**[2]  
6. **Regular expenses**[2]  
7. **Collateral** (for secured lending)[2]  
8. **Other risk mitigants** such as guarantees, when available[2]

These items must be supported by appropriate and up-to-date evidence (e.g., payslips, bank statements, identification, residence proof) and documented for supervisory review[3][4].

**Reflection flags:**
- partially_supported: Institutions should collect employment details including type, sector, status and duration (The guideline requires employment information, but does not specify type, sector, status or duration.)
- partially_supported: Institutions should collect the source of repayment capacity such as income, bonuses, commissions and overtime (The guideline mentions source of repayment capacity but does not enumerate the examples given.)
- partially_supported: The required items must be supported by appropriate, up‑to‑date evidence (e.g., payslips, bank statements, ID, residence proof) and documented for supervisory review (Sources require up‑to‑date information and list evidence types, but do not explicitly state the documentation requirement for supervisory review.)

---

## D3 (content): What must a written outsourcing agreement for a critical or important function contain under the EBA guidelines?

**Key points:**
- minimum contents of the agreement (para 75), e.g. a clear description of the outsourced function, start and end date, notice periods
- whether sub-outsourcing of critical or important functions is permitted (para 76)
- if permitted, conditions for sub-outsourcing (para 78)

**Tools:** ['search_documents'] | **cited docs:** ['eba_gl_2019_02'] | **expected docs:** ['eba_gl_2019_02']

**Answer:**

Under the EBA Guidelines on outsourcing arrangements (EBA/GL/2019/02), a written outsourcing agreement for a **critical or important function** should set out **at least** the following elements [1]:

1. **A clear description of the outsourced function** to be provided.  
2. **The start date and end date** of the agreement (where applicable) and the **notice periods** for both the service provider and the institution/payment institution.  
3. **The governing law** of the agreement.  
4. **The parties’ financial obligations**.  
5. **Whether sub-outsourcing of the critical or important function (or material parts thereof) is permitted**, and, if so, the conditions for sub-outsourcing as specified in the Guidelines (Section 13.1).  
6. **The location(s) (regions or countries) where the function will be performed and/or where relevant data will be kept and processed**, including any storage locations and the conditions to be met (e.g., notification requirements).  

These items constitute the minimum content that the Guidelines state “should” be included in the outsourcing contract for critical or important functions.

**Reflection flags:**
- partially_supported: The listed items (a‑f) constitute the minimum content that the Guidelines state “should” be included in the outsourcing contract for critical or important functions. (The Guidelines also include items (g‑i), which the answer omits.)
- unsupported: The answer limits the required elements to six items, implying that items g‑i are not mandatory. (The source lists items g‑i as part of the required content, so the claim that they are not required is not supported.)

---

## D4 (content): Wann gilt ein Kunde als politisch exponierte Person und welche Pflichten folgen daraus?

**Key points:**
- definition of PEP incl. family members and close associates (AuA 7.1)
- clarifying PEP status as part of due diligence (AuA 5.4)
- enhanced due diligence for PEPs

**Tools:** ['query_documents', 'search_documents'] | **cited docs:** ['bafin_aua_gwg'] | **expected docs:** ['bafin_aua_gwg']

**Answer:**

**Wann ein Kunde als politisch exponierte Person (PEP) gilt**

Ein Kunde (bzw. sein wirtschaftlich Berechtigter) gilt als PEP, wenn das Institut im Rahmen seiner allgemeinen Sorgfaltspflichten nach § 10 Abs. 1 Nr. 4 GwG mit risikoorientierten Verfahren feststellt, dass es sich um  

* eine politisch exponierte Person im Sinne von § 1 Abs. 12 GwG,  
* ein Familienmitglied einer solchen Person (§ 1 Abs. 13 GwG) oder  
* eine der PEP bekanntermaßen nahestehende Person (§ 1 Abs. 14 GwG) handelt[4].  

Die reine Abklärung des PEP-Status ist **keine** verstärkte Sorgfaltspflicht, sondern muss für alle Vertragspartner gleich erfolgen[2].

**Folgende Pflichten ergeben sich, wenn ein Kunde als PEP identifiziert wird**

1. **Verstärkte Sorgfaltspflichten** nach § 15 GwG (höheres Risiko, daher erweiterte Prüfungen, fortlaufende Überwachung usw.; die konkreten Maßnahmen sind in Kapitel 7.1 der Auslegungshinweise beschrieben)[2].  
2. **Übermittlungspflicht**: Die im Rahmen von § 10 Abs. 1 Nr. 4 GwG ermittelten Angaben zum PEP-Status müssen an die zuständige Behörde übermittelt werden[3].  
3. **Dokumentations- und Aufbewahrungspflicht**: Das Institut muss Kopien und Unterlagen, die für die Durchführung der Sorgfaltspflichten erstellt wurden (z. B. Identifizierungsdokumente, Registerauszüge), auf Anfrage Dritter oder anderer geeigneter Stellen übermitteln und sie gemäß § 8 Abs. 4 GwG aufbewahren[3].  

Damit ist der Kunde als PEP klassifiziert, sobald die genannten Kriterien erfüllt sind, und das Institut muss die genannten erweiterten Prüf-, Melde- und Aufbewahrungspflichten erfüllen.

**Reflection flags:**
- unsupported: Factoring business is subject to enhanced due‑diligence under §25k Abs. 2 KWG. (No cited source addresses this KWG provision.)

---

## X1 (cross_lingual): How must the front office and back office be separated in lending under German rules?

**Key points:**
- Markt and Marktfolge separated up to management board level (BTO 1.1 Tz. 1)
- organisational separation also of Handel / Risikocontrolling (BTO Tz. 3)

**Tools:** ['query_documents', 'search_documents'] | **cited docs:** ['bafin_rs_06_2026'] | **expected docs:** ['bafin_rs_06_2026']

**Answer:**

Under the BaFin “Mindestanforderungen an das Risikomanagement” (Rundschreiben 06/2026) the **front office (Markt)** and **back office (Markt-Folge)** must be organised as separate units, and this separation must extend up to the level of senior management [1].  

For **risk-relevant credit decisions** the two units must each give an independent vote (the “two-vote principle”). Only when a loan is classified as non-risk-relevant, when the institution is very small and the management itself directly decides on the credit, or when the loan is initiated by a third party and the process is highly normed (e.g. housing-promotion loans), may a single vote be used [4].  

If a single-vote approach is chosen, the institution must still ensure that the overall credit-process requirements of the MaRisk are met [3].  

Any waiver of the organisational separation must be **proportionate** to the size and complexity of the credit business and must be justified by the institution [1].

---

## X2 (cross_lingual): Under MaRisk, which activities may a bank outsource and which risks must it manage?

**Key points:**
- activities and processes may in principle be outsourced (AT 9 Tz. 4)
- limits for control functions (AT 9 Tz. 5)
- the institution must manage the risks of outsourcing appropriately (AT 9 Tz. 9)

**Tools:** ['search_documents'] | **cited docs:** ['bafin_rs_06_2026'] | **expected docs:** ['bafin_rs_06_2026']

**Answer:**

**Activities that may be outsourced under MaRisk**

- **All activities and processes** may be outsourced provided that the outsourcing does **not impair the proper organisation of the business** under § 25a Abs. 1 KWG (e.g., no “empty-shell” situation) [1].  
- **Leadership tasks of the management** must **not** be outsourced [1].  
- **Activities and processes in control areas and core-banking areas** can be outsourced if the bank can guarantee **effective monitoring** of the services delivered by the outsourcing provider [3].  
- A **complete outsourcing of the risk-controlling function, the compliance function or internal audit** is permissible for **subsidiaries within a banking group**, provided that the outsourcing institution is **not classified as “significant”** with respect to size, complexity and risk profile for the national financial sector [3].  

**Risks that must be managed**

- The bank must carry out a **risk analysis** for every outsourcing arrangement (Tz. 2) and, for **essential outsourcing**, apply the **extended requirements** that take into account the significance of the outsourced activity [2].  
- The bank must **monitor the outsourced activities and processes** continuously, ensuring that the ability to supervise is not limited by **long or complex outsourcing chains** [2].  
- A **central outsourcing-management function** must be established, with responsibilities that include:  
  a) implementing and further developing an appropriate outsourcing-management framework together with control and monitoring processes,  
  b) maintaining a complete documentation register of all outsourcing (including onward outsourcing) per § 25b Abs. 1 Satz 4 KWG,  
  c) supporting business units on internal and regulatory outsourcing requirements, and  
  d) coordinating and reviewing the risk analyses performed by the relevant areas [4].  

In summary, MaRisk permits outsourcing of virtually any activity or process except senior management responsibilities, while obliging banks to manage the associated risks through thorough risk analysis, continuous oversight, proper documentation, and a dedicated outsourcing-management function.

**Reflection flags:**
- partially_supported: The bank must carry out a risk analysis for every outsourcing arrangement (Tz. 2) and, for essential outsourcing, apply extended requirements that consider the significance of the outsourced activity. (Source [2] mentions a risk analysis per Tz. 2 and extended requirements for essential outsourcing, but does not explicitly say it is required for *every* outsourcing arrangement.)

---

## X3 (cross_lingual): Welche Anforderungen gelten für die Videoidentifizierung bei der Fernkontoeröffnung?

**Key points:**
- answer in German
- liveness detection
- quality and lighting of the video
- trained employees / interview guide

**Tools:** ['search_documents', 'search_documents'] | **cited docs:** ['bafin_aua_gwg'] | **expected docs:** ['eba_gl_2022_15']

**Answer:**

Bei der Fernkontoeröffnung dürfen nach den Auslegungs- und Anwendungshinweisen zum Geldwäschegesetz (AuA GwG) die Verpflichteten unter Aufsicht der BaFin das **Videoidentifizierungsverfahren** einsetzen. Die konkreten Anforderungen an das Verfahren – etwa technische Sicherheitsstandards, Ablauf der Identitätsprüfung und Dokumentationspflichten – ergeben sich aus dem **BaFin-Rundschreiben 3/2017 (GW) vom 10. April 2017**, auf das in den Hinweisen verwiesen wird. Bis zur Veröffentlichung dieser Auslegungshinweise liegt darüber hinaus keine weiterführende Rechtsverordnung vor[1][2].

**Reflection flags:**
- partially_supported: The provisions described also apply specifically to remote account opening (Fernkontoeröffnung). (Sources discuss identity verification generally, not explicitly remote account opening.)

---

## H1 (chained): What do AML documents issued after 2022 say about enhanced due diligence for high-risk customers?

**Key points:**
- EBA: enhanced CDD under Article 18 for increased risk
- EBA: more than one reliable independent source
- BaFin: § 15 GwG reinforced due diligence, calibrated to risk
- BaFin: high-risk third countries

**Tools:** ['query_documents', 'search_documents', 'search_documents'] | **cited docs:** ['bafin_aua_gwg', 'eba_gl_2024_01'] | **expected docs:** ['eba_gl_2024_01', 'bafin_aua_gwg']

**Answer:**

**EBA – Guidelines amending the ML/TF Risk Factors Guidelines (2024)**  

* When a business relationship or occasional transaction is assessed as having a higher risk, the credit-or-investment-type service provider (CASP) **must apply enhanced customer-due-diligence (EDD) measures** in line with Article 18 of Directive (EU) 2015/849 and the list set out in Title I of the Guidelines[3].  
* The Guidelines give examples of the additional measures that may be required, such as:  
  – Verifying the customer’s and the beneficial owner’s identity using **more than one reliable and independent source**[3].  
  – Identifying and verifying the identity of majority shareholders or natural persons who can operate a crypto-asset account on the customer’s behalf[3].  
* For relationships involving **high-risk non-EU countries**, CASPs should follow the guidance in Title I (i.e., the same EDD approach)[5].  
* Paragraph 26 explicitly states that where the ML/TF risk assessment determines a **high level of risk**, the institution **should apply the EDD measures** laid down in Article 18 of the Fourth Anti-Money-Laundering Directive[6].  

**BaFin – Auslegungs- und Anwendungshinweise zum Geldwäschegesetz (2025)**  

* § 15 Abs. 3 Nr. 2 GwG defines a **minimum set of reinforced (enhanced) due-diligence obligations** for business relationships or transactions that involve a third country identified by the European Commission as high-risk. The exact scope may be expanded depending on the **individual risk level**[7].  
* § 15 Abs. 2 GwG provides a **general clause**: whenever a higher risk of money-laundering or terrorist financing is identified (including cases not listed in § 15 Abs. 3), the obliged entity must determine and implement **appropriate enhanced due-diligence measures** based on its risk analysis[9].  
* § 10 Abs. 2 Satz 3 GwG requires that, when assessing the risk and deciding on the **extent of enhanced due-diligence**, the entity must at least consider:  
  – the purpose of the account or business relationship,  
  – the amount of assets or transaction volume, and  
  – the regularity or duration of the relationship[10].  

**Summary** – Both post-2022 AML documents require that, for high-risk customers (e.g., those linked to high-risk third-countries, sectors, or crypto-asset services), institutions must move beyond standard CDD and apply **enhanced due-diligence measures**. The EBA guideline lists concrete verification steps, while the BaFin guidance ties the obligation to the statutory risk-based framework of §§ 10 and 15 GwG, allowing additional measures to be calibrated to the specific risk profile.

**Reflection flags:**
- partially_supported: Both post‑2022 AML documents require that, for high‑risk customers (e.g., linked to high‑risk third‑countries, sectors, or crypto‑asset services), institutions must move beyond standard CDD and apply enhanced due‑diligence measures. (The sources confirm EDD for high‑risk third‑countries and crypto‑asset cases, but do not explicitly mention ‘sectors’; the broader statement is a synthesis.)

---

## H2 (chained): Which document amended the EBA ML/TF Risk Factors Guidelines, and what does it say about crypto-asset service providers?

**Key points:**
- EBA/GL/2024/01 amends EBA/GL/2021/02
- it inserts a new sectoral Guideline 21 for crypto-asset service providers (para 35)
- CASPs must comply with Title I and the relevant sector-specific Title II provisions (21.2)
- specific risk factors and enhanced measures where risk is increased (e.g. 21.6, 21.12)

**Tools:** ['query_documents', 'search_documents'] | **cited docs:** ['eba_gl_2024_01'] | **expected docs:** ['eba_gl_2024_01']

**Answer:**

The **EBA Guidelines amending the ML/TF Risk Factors Guidelines (EBA/GL/2024/01)** amend the original ML/TF Risk Factors Guidelines (EBA/GL/2021/02)[1].

**What the amendment says about crypto-asset service providers (CASPs):**

* CASPs must comply with the general provisions of Title I of the ML/TF Risk Factors Guidelines **and** with the sector-specific provisions set out in Title II that are relevant to the CASP’s product offering[2].  
* A new “Guideline 21” is inserted, titled **“Sectoral Guideline for crypto-asset services providers (CASPs)”**[3].  
* The guideline identifies specific risk-factor scenarios for CASPs, for example when a customer requests an exchange involving a crypto-asset account or a distributed-ledger address that is hosted by a CASP or another crypto-asset service provider regulated under Regulation (EU) 2023/1114, especially when the counterpart is in a jurisdiction with robust AML/CFT standards or is deemed low-risk[4].  
* It also notes that risk can be reduced when the transfer originates from or is sent to a crypto-asset account or distributed-ledger address hosted by a CASP (or a non-CASP crypto-asset service provider) that operates in a jurisdiction with low ML/TF risk levels[5].  

These provisions introduce a dedicated sectoral framework for CASPs within the broader ML/TF risk-factor regime.

**Reflection flags:**
- partially_supported: CASPs must comply with Title I provisions and sector‑specific Title II provisions relevant to their product offering (Source says CASPs "should" comply, not that they "must".)
- unsupported: These provisions create a dedicated sectoral framework for CASPs within the broader ML/TF risk‑factor regime (No source is cited for this summarising statement.)

---

## H3 (chained): Compare the EBA and BaFin requirements on outsourcing.

**Key points:**
- EBA: minimum contents of the written agreement for critical or important functions (EBA/GL/2019/02 para 75)
- MaRisk: a risk analysis determines which outsourcings are material / wesentlich (AT 9 Tz. 2)
- MaRisk: outsourcing of control and core banking functions only to an extent that keeps effective monitoring (AT 9 Tz. 5)
- MaRisk: the institution must manage outsourcing risks and monitor the provider (AT 9 Tz. 9)
- each document searched separately

**Tools:** ['search_documents', 'search_documents'] | **cited docs:** ['bafin_rs_06_2026', 'eba_gl_2019_02'] | **expected docs:** ['eba_gl_2019_02', 'bafin_rs_06_2026']

**Answer:**

**Scope and definition**  
*EBA*: The guideline defines outsourcing in terms of the transfer of activities to a service provider but does not give a formal definition; it focuses on the need for a policy that distinguishes different types of arrangements [1].  
*BaFin*: The circular gives a concrete definition – outsourcing occurs when another company is commissioned to perform activities and processes that would otherwise be carried out by the institution itself, and civil-law arrangements cannot exclude the existence of outsourcing [6].

**Policy and categorisation**  
*EBA*: Institutions must adopt an outsourcing policy that distinguishes (a) critical/important functions from other functions, (b) authorised versus non-authorised service providers, (c) intra-group versus external providers, and (d) providers located in the EU versus third countries [1].  
*BaFin*: The circular does not prescribe a categorical matrix, but it requires that the outsourcing contract contain “consent reservations” or concrete conditions for any further sub-outsourcing (Weiterverlagerungen) [5].

**Responsibility and accountability**  
*EBA*: Outsourcing must not result in the delegation of the management body’s responsibilities; the institution remains fully responsible and accountable for all regulatory obligations, including oversight of critical or important functions [4].  
*BaFin*: Likewise, outsourcing is permissible only insofar as it does not impair the proper organisation of the business under § 25a Abs. 1 KWG; the management’s duties may not be delegated to the outsourcing provider [7].

**Oversight, competence and suitability**  
*EBA*: The guideline stresses that outsourcing must not lower the suitability requirements for members of the management body, directors, key function holders, and that institutions must have adequate competence and appropriately skilled resources to manage and oversee outsourcing arrangements [3].  
*BaFin*: The circular requires the institution to verify regularly that the outsourcing arrangement meets supervisory requirements, and it allows the internal audit function to forego its own testing only if another audit satisfies the supervisory standards and the results are communicated [7].

**Sub-outsourcing (sub-contracting)**  
*EBA*: The outsourcing agreement must state whether sub-outsourcing of critical or important functions (or material parts thereof) is permitted [2].  
*BaFin*: The circular goes further, obliging the contract to include information duties for the service provider and to ensure that any sub-outsourcing aligns with the original outsourcing contract; the sub-outsourcer remains reporting-obliged to the institution [5].

**Control-area and core-banking functions**  
*EBA*: No specific exemption or allowance is mentioned for outsourcing of control-area functions.  
*BaFin*: Outsourcing of activities in control areas and core-banking functions is allowed provided effective monitoring is ensured and the institution can continue operations after termination. Full outsourcing of risk-controlling, compliance or internal audit is permissible for subsidiaries, provided the parent institution is not deemed essential for the national financial sector [8].

**Summary of key differences**  

| Aspect | EBA (Guidelines on outsourcing) | BaFin (Rundschreiben 06/2026) |
|--------|----------------------------------|------------------------------|
| Definition | Implicit; focus on policy categories | Explicit definition; civil-law forms cannot exclude outsourcing |
| Policy categorisation | Detailed matrix (criticality, authorisation, intra-group, location) | No matrix; emphasis on consent clauses for sub-outsourcing |
| Delegation of management | Explicit prohibition of delegating management body responsibilities | Same prohibition, linked to § 25a KWG |
| Suitability & competence | Must not lower suitability of management and key function holders; require adequate resources | Requires regular verification of compliance; internal audit may rely on other audits under conditions |
| Sub-outsourcing | Must be addressed in the agreement (permitted or not) | Must be contractually controlled, with information and reporting obligations |
| Control-area functions | No specific guidance | Allows outsourcing if monitoring is effective; full outsourcing of risk, compliance, internal audit possible for subsidiaries under size/complexity conditions |

Overall, both regulators stress that the institution retains ultimate responsibility and must maintain effective oversight. The EBA guideline is more prescriptive about policy categorisation and suitability of senior staff, whereas BaFin provides a detailed contractual framework for sub-outsourcing and explicit allowances for outsourcing of control-area functions, especially for subsidiaries.  

**Sources**: EBA guideline passages [1][2][3][4]; BaFin circular passages [5][6][7][8].

**Reflection flags:**
- unsupported: The EBA guideline does not give a formal definition of outsourcing, only an implicit one focused on policy categories. (Source [1] lists policy categories but does not state that the EBA lacks a formal definition.)
- unsupported: The EBA guideline provides no specific exemption or allowance for outsourcing of control‑area functions. (No source is cited for this claim, and the EBA guideline does not contain an explicit statement on such an exemption.)

---

## N1 (not_in_corpus): Which EBA guideline does Rundschreiben 14/2026 adopt, and what does that guideline require?

**Key points:**
- adopts EBA/GL/2026/01
- states that the content of EBA/GL/2026/01 is NOT in the corpus
- does not invent its requirements

**Tools:** ['query_documents'] | **cited docs:** ['bafin_rs_14_2026'] | **expected docs:** ['bafin_rs_14_2026']

**Answer:**

Rundschreiben 14/2026 (BaFin) adopts the European Banking Authority guideline identified as **EBA/GL/2026/01** [1].  

The corpus does not contain the text of that EBA guideline, so its specific requirements cannot be retrieved from the available documents.

**Reflection flags:**
- unsupported: The corpus does not contain the text of the EBA guideline EBA/GL/2026/01 (The source only lists the catalogue entry and does not mention whether the guideline text is present in the corpus.)
- unsupported: Specific requirements of the guideline cannot be retrieved from the available documents (The source provides no information about the availability of the guideline’s content.)

---

## N2 (not_in_corpus): What does the EU AI Act require for credit scoring models?

**Key points:**
- states that the documents do not cover the EU AI Act
- does not answer from memory

**Tools:** ['search_documents'] | **cited docs:** [] | **expected docs:** []

**Answer:**

The corpus does not contain the text of the EU AI Act, so its specific requirements for credit-scoring models are not available here.

**Reflection flags:**
- no_sources: Whole answer (The answer cites no sources (for example because it says the information is not available), so there is nothing to verify.)

---
