--
-- PostgreSQL database dump
--

\restrict 2vJXHYbPV2YibMBPOtjBWHlwpDBU3SXXe8y3yzS8gXlHA5yeaFbDWirtnDs2gV0

-- Dumped from database version 16.14 (Homebrew)
-- Dumped by pg_dump version 16.14 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: saulcortes
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO saulcortes;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: saulcortes
--

COMMENT ON SCHEMA public IS '';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO saulcortes;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.audit_logs (
    user_id integer,
    action character varying(120) NOT NULL,
    entity character varying(120) NOT NULL,
    entity_id integer,
    previous_values json,
    new_values json,
    comment character varying(500),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO saulcortes;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO saulcortes;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: calibration_procedures; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.calibration_procedures (
    code character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    magnitude character varying(80) NOT NULL,
    profile_key character varying(80),
    version character varying(40) NOT NULL,
    issuer_company character varying(40) NOT NULL,
    certificate_type character varying(40) NOT NULL,
    required_readings integer,
    decision_rule text,
    acceptance_criteria text,
    notes text,
    status character varying(40) NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    uncertainty_model_id integer,
    uncertainty_model_version_id integer
);


ALTER TABLE public.calibration_procedures OWNER TO saulcortes;

--
-- Name: calibration_procedures_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.calibration_procedures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.calibration_procedures_id_seq OWNER TO saulcortes;

--
-- Name: calibration_procedures_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.calibration_procedures_id_seq OWNED BY public.calibration_procedures.id;


--
-- Name: catalog_items; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.catalog_items (
    item_type character varying(20) NOT NULL,
    commodity character varying(40) NOT NULL,
    category character varying(120) NOT NULL,
    internal_key character varying(80),
    name character varying(180) NOT NULL,
    description text,
    sat_key character varying(40),
    sat_unit character varying(40),
    internal_unit character varying(80),
    origin_price numeric(12,2) NOT NULL,
    origin_currency character varying(3) NOT NULL,
    exchange_rate numeric(12,6) NOT NULL,
    margin_percent numeric(8,4) NOT NULL,
    final_price_mxn numeric(12,2) NOT NULL,
    internal_cost numeric(12,2),
    cost_currency character varying(3),
    calibration_scope character varying(60),
    quotation_legend text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    custom_internal_unit character varying(80),
    tax_object character varying(20) DEFAULT 'iva_16'::character varying NOT NULL,
    tax_rate numeric(5,2) DEFAULT 16.00 NOT NULL
);


ALTER TABLE public.catalog_items OWNER TO saulcortes;

--
-- Name: catalog_items_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.catalog_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.catalog_items_id_seq OWNER TO saulcortes;

--
-- Name: catalog_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.catalog_items_id_seq OWNED BY public.catalog_items.id;


--
-- Name: certificates; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.certificates (
    folio character varying(40) NOT NULL,
    service_order_id integer NOT NULL,
    equipment_id integer NOT NULL,
    field_sheet_id integer,
    certificate_type character varying(40) NOT NULL,
    status character varying(60) NOT NULL,
    issued_on date,
    released_on date,
    title character varying(180),
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    expected_folio character varying(40),
    final_pdf_path character varying(255),
    final_pdf_original_filename character varying(255),
    final_pdf_uploaded_at timestamp with time zone,
    final_pdf_uploaded_by_id integer,
    capture_started_at timestamp with time zone,
    capture_started_by_id integer,
    sent_to_quality_at timestamp with time zone,
    sent_to_quality_by_id integer,
    quality_reviewed_at timestamp with time zone,
    quality_reviewed_by_id integer,
    quality_rejection_reason text,
    released_to_client_at timestamp with time zone,
    released_to_client_by_id integer,
    external_source character varying(40) DEFAULT 'excel'::character varying NOT NULL,
    match_status character varying(40) DEFAULT 'pending'::character varying NOT NULL,
    match_details json,
    client_visible boolean DEFAULT false NOT NULL,
    authentication_code character varying(40),
    authentication_hash character varying(64),
    authenticated_pdf_path character varying(255),
    authenticated_pdf_generated_at timestamp with time zone,
    authenticated_by_id integer,
    verification_url character varying(255)
);


ALTER TABLE public.certificates OWNER TO saulcortes;

--
-- Name: certificates_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.certificates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.certificates_id_seq OWNER TO saulcortes;

--
-- Name: certificates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.certificates_id_seq OWNED BY public.certificates.id;


--
-- Name: client_contacts; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.client_contacts (
    client_id integer NOT NULL,
    name character varying(180) NOT NULL,
    email character varying(255),
    phone character varying(40),
    "position" character varying(120),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.client_contacts OWNER TO saulcortes;

--
-- Name: client_contacts_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.client_contacts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.client_contacts_id_seq OWNER TO saulcortes;

--
-- Name: client_contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.client_contacts_id_seq OWNED BY public.client_contacts.id;


--
-- Name: clients; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.clients (
    legal_name character varying(255) NOT NULL,
    commercial_name character varying(255),
    rfc character varying(13),
    email character varying(255),
    phone character varying(40),
    tax_regime character varying(120),
    payment_terms character varying(120),
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.clients OWNER TO saulcortes;

--
-- Name: clients_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.clients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clients_id_seq OWNER TO saulcortes;

--
-- Name: clients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.clients_id_seq OWNED BY public.clients.id;


--
-- Name: controlled_document_versions; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.controlled_document_versions (
    document_id integer NOT NULL,
    revision character varying(80) NOT NULL,
    file_path character varying(255),
    original_filename character varying(255),
    mime_type character varying(120),
    checksum character varying(128),
    change_summary text,
    uploaded_by_id integer,
    approved_by_id integer,
    reviewed_by_id integer,
    status character varying(40) NOT NULL,
    effective_date date,
    uploaded_at timestamp with time zone DEFAULT now() NOT NULL,
    approved_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.controlled_document_versions OWNER TO saulcortes;

--
-- Name: controlled_document_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.controlled_document_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.controlled_document_versions_id_seq OWNER TO saulcortes;

--
-- Name: controlled_document_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.controlled_document_versions_id_seq OWNED BY public.controlled_document_versions.id;


--
-- Name: controlled_documents; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.controlled_documents (
    code character varying(80) NOT NULL,
    name character varying(255) NOT NULL,
    document_type character varying(60) NOT NULL,
    quality_level character varying(80),
    current_revision character varying(80),
    issue_date date,
    last_review_date date,
    effective_date date,
    retention_time character varying(120),
    digital_location character varying(255),
    status character varying(40) NOT NULL,
    description text,
    created_by_id integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.controlled_documents OWNER TO saulcortes;

--
-- Name: controlled_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.controlled_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.controlled_documents_id_seq OWNER TO saulcortes;

--
-- Name: controlled_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.controlled_documents_id_seq OWNED BY public.controlled_documents.id;


--
-- Name: document_interpretations; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.document_interpretations (
    document_id integer NOT NULL,
    document_version_id integer,
    name character varying(255) NOT NULL,
    interpretation_type character varying(80) NOT NULL,
    magnitude character varying(80),
    equipment_type character varying(120),
    service_type character varying(80),
    calibration_scope character varying(40),
    data json,
    status character varying(40) NOT NULL,
    version integer NOT NULL,
    created_by_id integer,
    approved_by_id integer,
    approved_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.document_interpretations OWNER TO saulcortes;

--
-- Name: document_interpretations_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.document_interpretations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_interpretations_id_seq OWNER TO saulcortes;

--
-- Name: document_interpretations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.document_interpretations_id_seq OWNED BY public.document_interpretations.id;


--
-- Name: document_templates; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.document_templates (
    template_key character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    company_name character varying(180) NOT NULL,
    company_tagline character varying(255),
    company_rfc character varying(20),
    company_email character varying(255),
    company_website character varying(255),
    company_address text,
    company_phone character varying(60),
    document_title character varying(120) NOT NULL,
    document_subtitle character varying(255),
    document_code character varying(80),
    document_revision character varying(80),
    document_issued_on date,
    terms_version character varying(80),
    commercial_terms text,
    metrological_terms text,
    legal_terms text,
    privacy_notice text,
    acceptance_text text,
    show_summary_terms boolean DEFAULT true NOT NULL,
    show_full_terms boolean DEFAULT true NOT NULL,
    show_acceptance_signature boolean DEFAULT true NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.document_templates OWNER TO saulcortes;

--
-- Name: document_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.document_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_templates_id_seq OWNER TO saulcortes;

--
-- Name: document_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.document_templates_id_seq OWNED BY public.document_templates.id;


--
-- Name: equipment; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.equipment (
    service_order_id integer NOT NULL,
    service_order_item_id integer,
    status character varying(60) NOT NULL,
    name character varying(180) NOT NULL,
    brand character varying(120),
    model character varying(120),
    serial_number character varying(120),
    internal_id character varying(120),
    range_or_capacity character varying(180),
    initial_condition text,
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.equipment OWNER TO saulcortes;

--
-- Name: equipment_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.equipment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.equipment_id_seq OWNER TO saulcortes;

--
-- Name: equipment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.equipment_id_seq OWNED BY public.equipment.id;


--
-- Name: field_sheet_reference_standards; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.field_sheet_reference_standards (
    field_sheet_id integer NOT NULL,
    reference_standard_id integer NOT NULL,
    usage_role character varying(40) NOT NULL,
    measurement_section character varying(80),
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    reference_standard_certificate_id integer,
    selected_uncertainty_id integer,
    selection_status character varying(40),
    selection_notes text,
    validation_snapshot json
);


ALTER TABLE public.field_sheet_reference_standards OWNER TO saulcortes;

--
-- Name: field_sheet_reference_standards_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.field_sheet_reference_standards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.field_sheet_reference_standards_id_seq OWNER TO saulcortes;

--
-- Name: field_sheet_reference_standards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.field_sheet_reference_standards_id_seq OWNED BY public.field_sheet_reference_standards.id;


--
-- Name: field_sheet_results; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.field_sheet_results (
    field_sheet_id integer NOT NULL,
    section_key character varying(80) NOT NULL,
    row_number integer NOT NULL,
    pattern_value character varying(180),
    ibc_value_1 character varying(180),
    ibc_value_2 character varying(180),
    ibc_value_3 character varying(180),
    unit character varying(80),
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.field_sheet_results OWNER TO saulcortes;

--
-- Name: field_sheet_results_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.field_sheet_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.field_sheet_results_id_seq OWNER TO saulcortes;

--
-- Name: field_sheet_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.field_sheet_results_id_seq OWNED BY public.field_sheet_results.id;


--
-- Name: field_sheets; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.field_sheets (
    equipment_id integer NOT NULL,
    status character varying(60) NOT NULL,
    initial_condition text,
    final_condition text,
    pattern_used character varying(180),
    results text,
    observations text,
    evidence_notes text,
    method character varying(180),
    environmental_conditions text,
    technician_notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    template_key character varying(40) NOT NULL,
    work_order_number integer,
    calibration_place character varying(180),
    reception_date date,
    calibration_date date,
    next_calibration_date date,
    environment_humidity_start character varying(40),
    environment_humidity_end character varying(40),
    environment_temperature_start character varying(40),
    environment_temperature_end character varying(40),
    equipment_general_condition boolean,
    consider_equipment_deviations boolean NOT NULL,
    units character varying(80),
    calibrated_by character varying(180),
    reviewed_by character varying(180),
    report_made_by character varying(180),
    purchase_order_or_quotation character varying(180),
    calibration_procedure_id integer,
    returned_to_technician_at timestamp with time zone,
    returned_to_technician_by_id integer,
    returned_to_technician_reason text
);


ALTER TABLE public.field_sheets OWNER TO saulcortes;

--
-- Name: field_sheets_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.field_sheets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.field_sheets_id_seq OWNER TO saulcortes;

--
-- Name: field_sheets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.field_sheets_id_seq OWNED BY public.field_sheets.id;


--
-- Name: quotation_items; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.quotation_items (
    quotation_id integer NOT NULL,
    service_name character varying(180) NOT NULL,
    description text,
    quantity integer NOT NULL,
    unit_price numeric(12,2) NOT NULL,
    total numeric(12,2) NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    catalog_item_id integer,
    unit character varying(80),
    currency character varying(3),
    commodity character varying(40),
    calibration_scope character varying(60),
    quotation_legend text,
    sat_key character varying(40),
    sat_unit character varying(40),
    internal_unit character varying(80),
    discount_percent numeric(8,4) DEFAULT 0.0000 NOT NULL,
    tax_object character varying(20),
    tax_rate numeric(5,2) DEFAULT 16.00 NOT NULL,
    tax_total numeric(12,2) DEFAULT 0.00 NOT NULL
);


ALTER TABLE public.quotation_items OWNER TO saulcortes;

--
-- Name: quotation_items_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.quotation_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quotation_items_id_seq OWNER TO saulcortes;

--
-- Name: quotation_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.quotation_items_id_seq OWNED BY public.quotation_items.id;


--
-- Name: quotations; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.quotations (
    folio character varying(40) NOT NULL,
    client_id integer NOT NULL,
    status character varying(40) NOT NULL,
    issued_on date,
    valid_until date,
    subtotal numeric(12,2) NOT NULL,
    tax_total numeric(12,2) NOT NULL,
    total numeric(12,2) NOT NULL,
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    advisor_id integer
);


ALTER TABLE public.quotations OWNER TO saulcortes;

--
-- Name: quotations_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.quotations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quotations_id_seq OWNER TO saulcortes;

--
-- Name: quotations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.quotations_id_seq OWNED BY public.quotations.id;


--
-- Name: reference_standard_certificate_uncertainties; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.reference_standard_certificate_uncertainties (
    certificate_id integer NOT NULL,
    magnitude character varying(80),
    measurement_type character varying(120),
    range_min numeric(18,6),
    range_max numeric(18,6),
    unit character varying(40),
    uncertainty_value numeric(18,6) NOT NULL,
    uncertainty_unit character varying(40),
    k_factor numeric(12,6),
    confidence_level character varying(80),
    distribution character varying(80),
    formula_reference character varying(180),
    notes text,
    is_active boolean NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reference_standard_certificate_uncertainties OWNER TO saulcortes;

--
-- Name: reference_standard_certificate_uncertainties_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.reference_standard_certificate_uncertainties_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_standard_certificate_uncertainties_id_seq OWNER TO saulcortes;

--
-- Name: reference_standard_certificate_uncertainties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.reference_standard_certificate_uncertainties_id_seq OWNED BY public.reference_standard_certificate_uncertainties.id;


--
-- Name: reference_standard_certificates; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.reference_standard_certificates (
    reference_standard_id integer NOT NULL,
    controlled_document_id integer,
    controlled_document_version_id integer,
    certificate_number character varying(120) NOT NULL,
    issuing_laboratory character varying(180),
    accreditation_body character varying(180),
    accreditation_number character varying(120),
    calibration_date date,
    expiration_date date,
    received_date date,
    status character varying(40) NOT NULL,
    is_current boolean NOT NULL,
    traceability_statement text,
    environmental_conditions text,
    notes text,
    created_by_id integer,
    approved_by_id integer,
    approved_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reference_standard_certificates OWNER TO saulcortes;

--
-- Name: reference_standard_certificates_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.reference_standard_certificates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_standard_certificates_id_seq OWNER TO saulcortes;

--
-- Name: reference_standard_certificates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.reference_standard_certificates_id_seq OWNED BY public.reference_standard_certificates.id;


--
-- Name: reference_standard_uncertainties; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.reference_standard_uncertainties (
    reference_standard_id integer NOT NULL,
    range_min numeric(18,6),
    range_max numeric(18,6),
    unit character varying(40),
    uncertainty_value numeric(18,6) NOT NULL,
    coverage_factor_k numeric(12,6),
    distribution character varying(80),
    notes text,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reference_standard_uncertainties OWNER TO saulcortes;

--
-- Name: reference_standard_uncertainties_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.reference_standard_uncertainties_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_standard_uncertainties_id_seq OWNER TO saulcortes;

--
-- Name: reference_standard_uncertainties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.reference_standard_uncertainties_id_seq OWNED BY public.reference_standard_uncertainties.id;


--
-- Name: reference_standards; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.reference_standards (
    internal_code character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    owner_company character varying(40) NOT NULL,
    magnitude character varying(80) NOT NULL,
    brand character varying(120),
    model character varying(120),
    serial_number character varying(120),
    identification character varying(120),
    unit character varying(40),
    range_min numeric(18,6),
    range_max numeric(18,6),
    resolution numeric(18,6),
    coverage_factor_k numeric(12,6),
    provider character varying(180),
    calibration_laboratory character varying(180),
    certificate_number character varying(120),
    certificate_file_path character varying(255),
    calibrated_on date,
    next_calibration_on date,
    status character varying(40) NOT NULL,
    notes text,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reference_standards OWNER TO saulcortes;

--
-- Name: reference_standards_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.reference_standards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_standards_id_seq OWNER TO saulcortes;

--
-- Name: reference_standards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.reference_standards_id_seq OWNED BY public.reference_standards.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.roles (
    name character varying(80) NOT NULL,
    description character varying(255),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.roles OWNER TO saulcortes;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO saulcortes;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: service_order_items; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.service_order_items (
    service_order_id integer NOT NULL,
    quotation_item_id integer,
    service_name character varying(180) NOT NULL,
    quantity integer NOT NULL,
    status character varying(60) NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.service_order_items OWNER TO saulcortes;

--
-- Name: service_order_items_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.service_order_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.service_order_items_id_seq OWNER TO saulcortes;

--
-- Name: service_order_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.service_order_items_id_seq OWNED BY public.service_order_items.id;


--
-- Name: service_orders; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.service_orders (
    folio character varying(40) NOT NULL,
    client_id integer NOT NULL,
    quotation_id integer,
    status character varying(60) NOT NULL,
    agenda_date date,
    closed_at date,
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    advisor_id integer,
    technician_id integer,
    service_date date,
    total_equipment integer NOT NULL,
    completed_equipment integer NOT NULL,
    requires_payment boolean NOT NULL,
    work_order_number integer NOT NULL
);


ALTER TABLE public.service_orders OWNER TO saulcortes;

--
-- Name: service_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.service_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.service_orders_id_seq OWNER TO saulcortes;

--
-- Name: service_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.service_orders_id_seq OWNED BY public.service_orders.id;


--
-- Name: technical_profile_allowed_patterns; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.technical_profile_allowed_patterns (
    technical_profile_id integer NOT NULL,
    pattern_id integer,
    pattern_code character varying(120),
    min_range numeric(18,6),
    max_range numeric(18,6),
    unit character varying(40),
    priority integer,
    is_preferred boolean NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id integer NOT NULL
);


ALTER TABLE public.technical_profile_allowed_patterns OWNER TO saulcortes;

--
-- Name: technical_profile_allowed_patterns_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.technical_profile_allowed_patterns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.technical_profile_allowed_patterns_id_seq OWNER TO saulcortes;

--
-- Name: technical_profile_allowed_patterns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.technical_profile_allowed_patterns_id_seq OWNED BY public.technical_profile_allowed_patterns.id;


--
-- Name: technical_profiles; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.technical_profiles (
    code character varying(120) NOT NULL,
    name character varying(255) NOT NULL,
    magnitude character varying(80) NOT NULL,
    equipment_type character varying(120) NOT NULL,
    service_type character varying(80) NOT NULL,
    calibration_scope character varying(40) NOT NULL,
    procedure_document_id integer,
    procedure_interpretation_id integer,
    field_sheet_template_document_id integer,
    certificate_template_document_id integer,
    uncertainty_source_document_id integer,
    status character varying(40) NOT NULL,
    version integer NOT NULL,
    rules json,
    notes text,
    created_by_id integer,
    approved_by_id integer,
    approved_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.technical_profiles OWNER TO saulcortes;

--
-- Name: technical_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.technical_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.technical_profiles_id_seq OWNER TO saulcortes;

--
-- Name: technical_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.technical_profiles_id_seq OWNED BY public.technical_profiles.id;


--
-- Name: uncertainty_calculations; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_calculations (
    field_sheet_id integer NOT NULL,
    uncertainty_model_id integer NOT NULL,
    status character varying(40) NOT NULL,
    calculated_at timestamp with time zone NOT NULL,
    calculation_snapshot json NOT NULL,
    input_snapshot json NOT NULL,
    component_results json NOT NULL,
    formula_results json NOT NULL,
    warnings json NOT NULL,
    errors json NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    uncertainty_model_version_id integer
);


ALTER TABLE public.uncertainty_calculations OWNER TO saulcortes;

--
-- Name: uncertainty_calculations_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_calculations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_calculations_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_calculations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_calculations_id_seq OWNED BY public.uncertainty_calculations.id;


--
-- Name: uncertainty_components; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_components (
    model_id integer NOT NULL,
    key character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    source_type character varying(60) NOT NULL,
    distribution character varying(60),
    divisor double precision,
    sensitivity_coefficient double precision NOT NULL,
    value_expression text,
    required boolean NOT NULL,
    sort_order integer NOT NULL,
    metadata_json json,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    model_version_id integer
);


ALTER TABLE public.uncertainty_components OWNER TO saulcortes;

--
-- Name: uncertainty_components_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_components_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_components_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_components_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_components_id_seq OWNED BY public.uncertainty_components.id;


--
-- Name: uncertainty_formulas; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_formulas (
    model_id integer NOT NULL,
    key character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    expression text NOT NULL,
    result_key character varying(80) NOT NULL,
    description text,
    sort_order integer NOT NULL,
    is_active_formula boolean NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    model_version_id integer
);


ALTER TABLE public.uncertainty_formulas OWNER TO saulcortes;

--
-- Name: uncertainty_formulas_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_formulas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_formulas_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_formulas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_formulas_id_seq OWNED BY public.uncertainty_formulas.id;


--
-- Name: uncertainty_model_exceptions; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_model_exceptions (
    base_model_id integer,
    alternate_model_id integer NOT NULL,
    magnitude character varying(80),
    equipment_type character varying(180),
    equipment_model character varying(120),
    procedure_id integer,
    profile_key character varying(80),
    reason text NOT NULL,
    authorized_by_id integer,
    authorized_at timestamp with time zone,
    status character varying(40) NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    base_model_version_id integer,
    alternate_model_version_id integer
);


ALTER TABLE public.uncertainty_model_exceptions OWNER TO saulcortes;

--
-- Name: uncertainty_model_exceptions_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_model_exceptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_model_exceptions_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_model_exceptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_model_exceptions_id_seq OWNED BY public.uncertainty_model_exceptions.id;


--
-- Name: uncertainty_model_versions; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_model_versions (
    model_id integer NOT NULL,
    version_number character varying(40) NOT NULL,
    status character varying(40) DEFAULT 'draft'::character varying NOT NULL,
    change_summary text,
    default_coverage_factor double precision DEFAULT '2'::double precision NOT NULL,
    submitted_at timestamp with time zone,
    submitted_by_id integer,
    approved_at timestamp with time zone,
    approved_by_id integer,
    obsolete_at timestamp with time zone,
    archived_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.uncertainty_model_versions OWNER TO saulcortes;

--
-- Name: uncertainty_model_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_model_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_model_versions_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_model_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_model_versions_id_seq OWNED BY public.uncertainty_model_versions.id;


--
-- Name: uncertainty_models; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_models (
    code character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    magnitude character varying(80) NOT NULL,
    equipment_family character varying(120),
    version character varying(40) NOT NULL,
    status character varying(40) NOT NULL,
    default_coverage_factor double precision NOT NULL,
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.uncertainty_models OWNER TO saulcortes;

--
-- Name: uncertainty_models_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_models_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_models_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_models_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_models_id_seq OWNED BY public.uncertainty_models.id;


--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.user_roles (
    user_id integer NOT NULL,
    role_id integer NOT NULL
);


ALTER TABLE public.user_roles OWNER TO saulcortes;

--
-- Name: users; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.users (
    email character varying(255) NOT NULL,
    full_name character varying(180) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    role_id integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.users OWNER TO saulcortes;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO saulcortes;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: calibration_procedures id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.calibration_procedures ALTER COLUMN id SET DEFAULT nextval('public.calibration_procedures_id_seq'::regclass);


--
-- Name: catalog_items id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.catalog_items ALTER COLUMN id SET DEFAULT nextval('public.catalog_items_id_seq'::regclass);


--
-- Name: certificates id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates ALTER COLUMN id SET DEFAULT nextval('public.certificates_id_seq'::regclass);


--
-- Name: client_contacts id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.client_contacts ALTER COLUMN id SET DEFAULT nextval('public.client_contacts_id_seq'::regclass);


--
-- Name: clients id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.clients ALTER COLUMN id SET DEFAULT nextval('public.clients_id_seq'::regclass);


--
-- Name: controlled_document_versions id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions ALTER COLUMN id SET DEFAULT nextval('public.controlled_document_versions_id_seq'::regclass);


--
-- Name: controlled_documents id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_documents ALTER COLUMN id SET DEFAULT nextval('public.controlled_documents_id_seq'::regclass);


--
-- Name: document_interpretations id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations ALTER COLUMN id SET DEFAULT nextval('public.document_interpretations_id_seq'::regclass);


--
-- Name: document_templates id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_templates ALTER COLUMN id SET DEFAULT nextval('public.document_templates_id_seq'::regclass);


--
-- Name: equipment id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.equipment ALTER COLUMN id SET DEFAULT nextval('public.equipment_id_seq'::regclass);


--
-- Name: field_sheet_reference_standards id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards ALTER COLUMN id SET DEFAULT nextval('public.field_sheet_reference_standards_id_seq'::regclass);


--
-- Name: field_sheet_results id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_results ALTER COLUMN id SET DEFAULT nextval('public.field_sheet_results_id_seq'::regclass);


--
-- Name: field_sheets id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets ALTER COLUMN id SET DEFAULT nextval('public.field_sheets_id_seq'::regclass);


--
-- Name: quotation_items id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotation_items ALTER COLUMN id SET DEFAULT nextval('public.quotation_items_id_seq'::regclass);


--
-- Name: quotations id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotations ALTER COLUMN id SET DEFAULT nextval('public.quotations_id_seq'::regclass);


--
-- Name: reference_standard_certificate_uncertainties id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificate_uncertainties ALTER COLUMN id SET DEFAULT nextval('public.reference_standard_certificate_uncertainties_id_seq'::regclass);


--
-- Name: reference_standard_certificates id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates ALTER COLUMN id SET DEFAULT nextval('public.reference_standard_certificates_id_seq'::regclass);


--
-- Name: reference_standard_uncertainties id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_uncertainties ALTER COLUMN id SET DEFAULT nextval('public.reference_standard_uncertainties_id_seq'::regclass);


--
-- Name: reference_standards id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standards ALTER COLUMN id SET DEFAULT nextval('public.reference_standards_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: service_order_items id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_order_items ALTER COLUMN id SET DEFAULT nextval('public.service_order_items_id_seq'::regclass);


--
-- Name: service_orders id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders ALTER COLUMN id SET DEFAULT nextval('public.service_orders_id_seq'::regclass);


--
-- Name: technical_profile_allowed_patterns id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profile_allowed_patterns ALTER COLUMN id SET DEFAULT nextval('public.technical_profile_allowed_patterns_id_seq'::regclass);


--
-- Name: technical_profiles id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles ALTER COLUMN id SET DEFAULT nextval('public.technical_profiles_id_seq'::regclass);


--
-- Name: uncertainty_calculations id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_calculations_id_seq'::regclass);


--
-- Name: uncertainty_components id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_components ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_components_id_seq'::regclass);


--
-- Name: uncertainty_formulas id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_formulas ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_formulas_id_seq'::regclass);


--
-- Name: uncertainty_model_exceptions id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_model_exceptions_id_seq'::regclass);


--
-- Name: uncertainty_model_versions id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_model_versions_id_seq'::regclass);


--
-- Name: uncertainty_models id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_models ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_models_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.alembic_version (version_num) FROM stdin;
a8b9c0d1e2f3
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.audit_logs (user_id, action, entity, entity_id, previous_values, new_values, comment, id, created_at, updated_at) FROM stdin;
\N	user.created	users	1	null	{"email": "saul@myc.com", "full_name": "admin", "is_active": true, "role_names": ["Administrador"]}	Registro inicial o alta desde auth.register	1	2026-06-30 12:50:53.013335-06	2026-06-30 12:50:53.013335-06
\N	client.created	clients	1	null	{"legal_name": "prueba", "rfc": "FIWUENFIOUWN"}	\N	2	2026-06-30 13:08:02.939115-06	2026-06-30 13:08:02.939115-06
\N	quotation.created	quotations	1	null	{"folio": "MYC-06-26-0001", "client_id": 1, "total": "0.00"}	\N	3	2026-06-30 13:08:57.560275-06	2026-06-30 13:08:57.560275-06
\N	catalog_item.created	catalog_items	1	null	{"name": "Servicio de calibraci\\u00f3n a b\\u00e1scula", "internal_key": "SER-CAL-0001"}	\N	4	2026-06-30 13:14:57.000475-06	2026-06-30 13:14:57.000475-06
\N	quotation.updated	quotations	1	{"valid_until": "2026-07-01", "notes": null}	{"valid_until": "2026-07-01", "notes": null}	\N	5	2026-06-30 13:16:31.843704-06	2026-06-30 13:16:31.843704-06
\N	quotation.sent	quotations	1	{"status": "draft"}	{"status": "sent"}	\N	6	2026-06-30 13:16:40.161056-06	2026-06-30 13:16:40.161056-06
\N	quotation.waiting	quotations	1	{"status": "sent"}	{"status": "waiting"}	\N	7	2026-06-30 13:16:42.16284-06	2026-06-30 13:16:42.16284-06
\N	quotation.accepted	quotations	1	{"status": "waiting"}	{"status": "accepted"}	\N	8	2026-06-30 13:16:45.3779-06	2026-06-30 13:16:45.3779-06
\N	service_order.created	service_orders	1	null	{"folio": "OSMYC-26-06-0001", "work_order_number": 7001, "client_id": 1, "quotation_id": 1, "status": "scheduled"}	\N	9	2026-06-30 13:16:48.34536-06	2026-06-30 13:16:48.34536-06
\N	equipment.created	equipment	1	null	{"service_order_id": 1, "name": "b\\u00e1scula", "status": "registered"}	\N	10	2026-06-30 13:20:14.879019-06	2026-06-30 13:20:14.879019-06
\N	field_sheet.created	field_sheets	1	null	{"equipment_id": 1, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7001, "status": "draft", "calibration_place": null, "reception_date": "2026-06-30", "calibration_date": null, "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0001", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 1, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 2, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 3, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 4, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 5, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 6, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 7, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 8, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 9, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 10, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	11	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
\N	field_sheet.procedure_assigned	field_sheets	1	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	12	2026-06-30 13:31:07.09876-06	2026-06-30 13:31:07.09876-06
\N	field_sheet.updated	field_sheets	1	{"equipment_id": 1, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7001, "status": "draft", "calibration_place": null, "reception_date": "2026-06-30", "calibration_date": null, "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0001", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 1, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 2, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 3, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 4, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 5, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 6, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 7, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 8, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 9, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 10, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 1, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7001, "status": "in_progress", "calibration_place": "lab myc", "reception_date": "2026-06-30", "calibration_date": "2026-06-26", "next_calibration_date": "2027-06-30", "environment_humidity_start": "32", "environment_humidity_end": "23", "environment_temperature_start": "32", "environment_temperature_end": "32", "equipment_general_condition": true, "consider_equipment_deviations": false, "units": "g", "calibrated_by": "miguel mu\\u00f1oz", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0001", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "buen estado", "evidence_notes": null, "method": null, "environmental_conditions": "ok", "technician_notes": null, "results_rows": [{"id": 1, "section_key": "main", "row_number": 1, "pattern_value": "323", "ibc_value_1": "43", "ibc_value_2": "34", "ibc_value_3": "43", "unit": "g", "notes": null}, {"id": 2, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 3, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 4, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 5, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 6, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 7, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 8, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 9, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 10, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	13	2026-06-30 13:31:07.09876-06	2026-06-30 13:31:07.09876-06
\N	field_sheet.procedure_assigned	field_sheets	1	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	14	2026-06-30 13:31:07.940354-06	2026-06-30 13:31:07.940354-06
\N	field_sheet.updated	field_sheets	1	{"equipment_id": 1, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7001, "status": "in_progress", "calibration_place": "lab myc", "reception_date": "2026-06-30", "calibration_date": "2026-06-26", "next_calibration_date": "2027-06-30", "environment_humidity_start": "32", "environment_humidity_end": "23", "environment_temperature_start": "32", "environment_temperature_end": "32", "equipment_general_condition": true, "consider_equipment_deviations": false, "units": "g", "calibrated_by": "miguel mu\\u00f1oz", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0001", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "buen estado", "evidence_notes": null, "method": null, "environmental_conditions": "ok", "technician_notes": null, "results_rows": [{"id": 1, "section_key": "main", "row_number": 1, "pattern_value": "323", "ibc_value_1": "43", "ibc_value_2": "34", "ibc_value_3": "43", "unit": "g", "notes": null}, {"id": 2, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 3, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 4, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 5, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 6, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 7, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 8, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 9, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 10, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 1, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7001, "status": "in_progress", "calibration_place": "lab myc", "reception_date": "2026-06-30", "calibration_date": "2026-06-26", "next_calibration_date": "2027-06-30", "environment_humidity_start": "32", "environment_humidity_end": "23", "environment_temperature_start": "32", "environment_temperature_end": "32", "equipment_general_condition": true, "consider_equipment_deviations": false, "units": "g", "calibrated_by": "miguel mu\\u00f1oz", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0001", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "buen estado", "evidence_notes": null, "method": null, "environmental_conditions": "ok", "technician_notes": null, "results_rows": [{"id": 1, "section_key": "main", "row_number": 1, "pattern_value": "323", "ibc_value_1": "43", "ibc_value_2": "34", "ibc_value_3": "43", "unit": "g", "notes": null}, {"id": 2, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 3, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 4, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 5, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 6, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 7, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 8, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 9, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 10, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	15	2026-06-30 13:31:07.940354-06	2026-06-30 13:31:07.940354-06
\N	field_sheet.completed	field_sheets	1	{"status": "in_progress", "equipment_status": "registered"}	{"status": "completed", "equipment_status": "calibrated", "certificate_ready": true, "external_certificate_flow": true}	\N	16	2026-06-30 13:31:07.97641-06	2026-06-30 13:31:07.97641-06
\N	field_sheet.reviewed	field_sheets	1	{"status": "completed"}	{"status": "under_review"}	\N	17	2026-06-30 13:31:44.746784-06	2026-06-30 13:31:44.746784-06
\N	service_order.confirmed	service_orders	1	{"status": "scheduled"}	{"status": "confirmed"}	\N	18	2026-06-30 15:06:15.229225-06	2026-06-30 15:06:15.229225-06
\N	service_order.called	service_orders	1	{"status": "confirmed"}	{"status": "called"}	\N	19	2026-06-30 15:06:17.505963-06	2026-06-30 15:06:17.505963-06
\N	service_order.in_progress	service_orders	1	{"status": "called"}	{"status": "in_progress"}	\N	20	2026-06-30 15:06:19.139296-06	2026-06-30 15:06:19.139296-06
\N	service_order.capture	service_orders	1	{"status": "in_progress"}	{"status": "capture"}	\N	21	2026-06-30 15:06:20.672404-06	2026-06-30 15:06:20.672404-06
\N	service_order.quality_review	service_orders	1	{"status": "capture"}	{"status": "quality_review"}	\N	22	2026-06-30 15:06:22.655818-06	2026-06-30 15:06:22.655818-06
\N	certificate.bulk_pdf_upload	service_orders	1	null	{"service_order_id": 1, "expected": 0, "uploaded": 1, "matched": 0, "warnings": 0, "mismatches": 0, "missing": 0}	\N	23	2026-06-30 15:06:50.436361-06	2026-06-30 15:06:50.436361-06
\N	certificate.expected_created	certificates	1	null	{"folio": "MYCT-06-2026-0001", "expected_folio": "MYCT-06-2026-0001", "service_order_id": 1, "equipment_id": 1, "field_sheet_id": 1, "status": "expected"}	\N	24	2026-06-30 15:07:04.089481-06	2026-06-30 15:07:04.089481-06
\N	certificate.capture_started	certificates	1	{"status": "expected"}	{"status": "capture_in_progress", "capture_started_at": "2026-06-30T21:07:12.829689+00:00"}	\N	25	2026-06-30 15:07:12.823962-06	2026-06-30 15:07:12.823962-06
\N	certificate.pdf_uploaded	certificates	1	null	{"filename": "MYCA-01-26-3281 TERMOMETRO DE CARATULA TE-NBF-10 PROX CAL 2027-01-26.pdf", "match_status": "mismatch", "status": "capture_in_progress"}	\N	26	2026-06-30 15:07:17.664893-06	2026-06-30 15:07:17.664893-06
\N	certificate.pdf_match_validated	certificates	1	null	{"match_status": "mismatch", "score": 0}	\N	27	2026-06-30 15:07:17.664893-06	2026-06-30 15:07:17.664893-06
\N	certificate.pdf_match_validated	certificates	1	null	{"match_status": "mismatch", "score": 0}	\N	28	2026-06-30 15:07:20.038683-06	2026-06-30 15:07:20.038683-06
\N	certificate.sent_to_quality	certificates	1	{"status": "capture_in_progress"}	{"status": "ready_for_quality", "sent_to_quality_at": "2026-06-30T21:07:21.263310+00:00"}	\N	29	2026-06-30 15:07:21.256896-06	2026-06-30 15:07:21.256896-06
\N	certificate.quality_approved	certificates	1	{"status": "ready_for_quality"}	{"status": "pdf_uploaded", "quality_reviewed_at": "2026-06-30T21:07:26.178129+00:00"}	\N	31	2026-06-30 15:07:26.169438-06	2026-06-30 15:07:26.169438-06
\N	certificate.pdf_authenticated	certificates	1	null	{"authentication_code": "MYC-AUTH-2026-000001", "authentication_hash": "074f6f2c3e97c4dc84985580d389edc9b12ad86a74687af78df5eafceec443db", "authenticated_pdf_path": "/Users/saulcortes/Desktop/myc_erp/storage/certificados/7001/MYCT-06-2026-0001_MYCA-01-26-3281_TERMOMETRO_DE_CARATULA_TE-NBF-10_PROX_CAL_2027-01-26_autenticado_MYC-AUTH-2026-000001.pdf"}	\N	32	2026-06-30 15:07:27.486817-06	2026-06-30 15:07:27.486817-06
\N	certificate.pdf_match_manual_accepted	certificates	1	null	{"match_status": "manual_accepted"}	Aceptado manualmente desde ETS	30	2026-06-30 15:07:24.654686-06	2026-06-30 15:07:24.654686-06
\N	certificate.pdf_authenticated	certificates	1	null	{"authentication_code": "MYC-AUTH-2026-000001", "authentication_hash": "074f6f2c3e97c4dc84985580d389edc9b12ad86a74687af78df5eafceec443db", "authenticated_pdf_path": "/Users/saulcortes/Desktop/myc_erp/storage/certificados/7001/MYCT-06-2026-0001_MYCA-01-26-3281_TERMOMETRO_DE_CARATULA_TE-NBF-10_PROX_CAL_2027-01-26_autenticado_MYC-AUTH-2026-000001.pdf"}	\N	33	2026-06-30 15:07:29.485351-06	2026-06-30 15:07:29.485351-06
\N	certificate.released_to_client	certificates	1	{"status": "pdf_uploaded"}	{"status": "released_to_client", "client_visible": true, "released_to_client_at": "2026-06-30T21:07:29.489256+00:00"}	\N	34	2026-06-30 15:07:29.485351-06	2026-06-30 15:07:29.485351-06
\N	equipment.labeled	equipment	1	{"status": "calibrated"}	{"status": "labeled"}	\N	35	2026-06-30 15:09:34.826942-06	2026-06-30 15:09:34.826942-06
\N	service_order.pending_payment	service_orders	1	{"status": "quality_review"}	{"status": "pending_payment"}	\N	36	2026-06-30 16:41:28.873151-06	2026-06-30 16:41:28.873151-06
\N	service_order.released	service_orders	1	{"status": "pending_payment"}	{"status": "released"}	\N	37	2026-06-30 16:41:32.252942-06	2026-06-30 16:41:32.252942-06
\N	quotation.deactivated	quotations	1	{"is_active": true}	{"is_active": false}	\N	38	2026-06-30 16:49:20.25349-06	2026-06-30 16:49:20.25349-06
\N	service_order.deactivated	service_orders	1	{"is_active": true}	{"is_active": false}	\N	39	2026-06-30 16:49:27.67771-06	2026-06-30 16:49:27.67771-06
\N	quotation.created	quotations	2	null	{"folio": "MYC-06-26-0002", "client_id": 1, "total": "0.00"}	\N	40	2026-06-30 16:49:44.274436-06	2026-06-30 16:49:44.274436-06
\N	quotation.item_added	quotations	2	null	{"service_name": "Servicio de calibraci\\u00f3n a b\\u00e1scula", "quantity": 8, "total": "9600.00"}	\N	41	2026-06-30 16:50:17.871668-06	2026-06-30 16:50:17.871668-06
\N	quotation.item_updated	quotations	2	{"catalog_item_id": 1, "service_name": "Servicio de calibraci\\u00f3n a b\\u00e1scula", "description": null, "quantity": 8, "unit": "service", "sat_key": "81141504", "sat_unit": "E48", "internal_unit": "service", "unit_price": "1200.00", "discount_percent": "0.0000", "currency": "MXN", "commodity": "calibration", "calibration_scope": "accredited_iso_17025", "quotation_legend": "Servicio acreditado ISO/IEC 17025:2017", "tax_object": "iva_16", "tax_rate": "16.00"}	{"catalog_item_id": 1, "service_name": "Servicio de calibraci\\u00f3n a b\\u00e1scula", "description": null, "quantity": 8, "unit": "service", "sat_key": "81141504", "sat_unit": "E48", "internal_unit": "service", "unit_price": "1200", "discount_percent": "0", "currency": "MXN", "commodity": "calibration", "calibration_scope": "accredited_iso_17025", "quotation_legend": "Servicio acreditado ISO/IEC 17025:2017", "tax_object": "iva_16", "tax_rate": "16", "quotation_total": "11136.00"}	\N	42	2026-06-30 16:50:22.588769-06	2026-06-30 16:50:22.588769-06
\N	quotation.updated	quotations	2	{"valid_until": "2026-06-17", "notes": null}	{"valid_until": "2026-07-02", "notes": null}	\N	43	2026-06-30 16:50:37.589261-06	2026-06-30 16:50:37.589261-06
\N	quotation.sent	quotations	2	{"status": "draft"}	{"status": "sent"}	\N	44	2026-06-30 16:50:41.370508-06	2026-06-30 16:50:41.370508-06
\N	quotation.waiting	quotations	2	{"status": "sent"}	{"status": "waiting"}	\N	45	2026-06-30 16:50:44.539175-06	2026-06-30 16:50:44.539175-06
\N	quotation.accepted	quotations	2	{"status": "waiting"}	{"status": "accepted"}	\N	46	2026-06-30 16:50:45.916285-06	2026-06-30 16:50:45.916285-06
\N	service_order.created	service_orders	2	null	{"folio": "OSMYC-26-06-0002", "work_order_number": 7002, "client_id": 1, "quotation_id": 2, "status": "scheduled"}	\N	47	2026-06-30 16:50:49.803401-06	2026-06-30 16:50:49.803401-06
\N	service_order.confirmed	service_orders	2	{"status": "scheduled"}	{"status": "confirmed"}	\N	48	2026-06-30 16:51:18.274813-06	2026-06-30 16:51:18.274813-06
\N	service_order.called	service_orders	2	{"status": "confirmed"}	{"status": "called"}	\N	49	2026-06-30 16:51:20.063996-06	2026-06-30 16:51:20.063996-06
\N	service_order.in_progress	service_orders	2	{"status": "called"}	{"status": "in_progress"}	\N	50	2026-06-30 16:51:24.244956-06	2026-06-30 16:51:24.244956-06
\N	equipment.created	equipment	2	null	{"service_order_id": 2, "name": "ewfwefewf", "status": "registered"}	\N	51	2026-06-30 16:51:42.392329-06	2026-06-30 16:51:42.392329-06
\N	field_sheet.created	field_sheets	2	null	{"equipment_id": 2, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7002, "status": "draft", "calibration_place": null, "reception_date": "2026-06-30", "calibration_date": null, "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 11, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 12, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 13, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 14, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 15, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 16, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 17, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 18, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 19, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 20, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	52	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
\N	field_sheet.procedure_assigned	field_sheets	2	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	53	2026-06-30 16:52:22.258667-06	2026-06-30 16:52:22.258667-06
\N	field_sheet.updated	field_sheets	2	{"equipment_id": 2, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7002, "status": "draft", "calibration_place": null, "reception_date": "2026-06-30", "calibration_date": null, "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 11, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 12, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 13, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 14, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 15, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 16, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 17, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 18, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 19, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 20, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 2, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7002, "status": "in_progress", "calibration_place": null, "reception_date": "2026-06-30", "calibration_date": null, "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 11, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "4039", "ibc_value_2": "2094", "ibc_value_3": "320", "unit": "kg", "notes": null}, {"id": 12, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 13, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 14, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 15, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 16, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 17, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 18, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 19, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 20, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	54	2026-06-30 16:52:22.258667-06	2026-06-30 16:52:22.258667-06
\N	field_sheet.procedure_assigned	field_sheets	2	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	55	2026-06-30 16:52:59.00768-06	2026-06-30 16:52:59.00768-06
\N	field_sheet.completed	field_sheets	2	{"status": "in_progress", "equipment_status": "registered"}	{"status": "completed", "equipment_status": "calibrated", "certificate_ready": true, "external_certificate_flow": true, "certificate_id": null, "certificate_status": null}	\N	59	2026-06-30 16:52:59.957256-06	2026-06-30 16:52:59.957256-06
\N	service_order.capture	service_orders	2	{"status": "in_progress"}	{"status": "capture"}	\N	61	2026-06-30 16:54:26.449654-06	2026-06-30 16:54:26.449654-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	126	2026-06-30 17:23:37.830697-06	2026-06-30 17:23:37.830697-06
\N	field_sheet.updated	field_sheets	2	{"equipment_id": 2, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7002, "status": "in_progress", "calibration_place": null, "reception_date": "2026-06-30", "calibration_date": null, "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 11, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "4039", "ibc_value_2": "2094", "ibc_value_3": "320", "unit": "kg", "notes": null}, {"id": 12, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 13, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 14, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 15, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 16, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 17, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 18, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 19, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 20, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 2, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7002, "status": "in_progress", "calibration_place": null, "reception_date": "2026-06-30", "calibration_date": "2026-07-02", "next_calibration_date": "2027-11-17", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 11, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "4039", "ibc_value_2": "2094", "ibc_value_3": "320", "unit": "kg", "notes": null}, {"id": 12, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 13, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 14, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 15, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 16, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 17, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 18, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 19, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 20, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	56	2026-06-30 16:52:59.00768-06	2026-06-30 16:52:59.00768-06
\N	field_sheet.procedure_assigned	field_sheets	2	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	57	2026-06-30 16:52:59.920617-06	2026-06-30 16:52:59.920617-06
\N	field_sheet.updated	field_sheets	2	{"equipment_id": 2, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7002, "status": "in_progress", "calibration_place": null, "reception_date": "2026-06-30", "calibration_date": "2026-07-02", "next_calibration_date": "2027-11-17", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 11, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "4039", "ibc_value_2": "2094", "ibc_value_3": "320", "unit": "kg", "notes": null}, {"id": 12, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 13, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 14, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 15, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 16, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 17, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 18, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 19, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 20, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 2, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7002, "status": "in_progress", "calibration_place": null, "reception_date": "2026-06-30", "calibration_date": "2026-07-02", "next_calibration_date": "2027-11-17", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 11, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "4039", "ibc_value_2": "2094", "ibc_value_3": "320", "unit": "kg", "notes": null}, {"id": 12, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 13, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 14, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 15, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 16, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 17, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 18, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 19, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 20, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	58	2026-06-30 16:52:59.920617-06	2026-06-30 16:52:59.920617-06
\N	field_sheet.reviewed	field_sheets	2	{"status": "completed"}	{"status": "under_review", "certificate_id": null, "certificate_status": null}	\N	60	2026-06-30 16:53:48.059354-06	2026-06-30 16:53:48.059354-06
\N	certificate.bulk_pdf_upload	service_orders	2	null	{"service_order_id": 2, "expected": 0, "uploaded": 1, "matched": 0, "warnings": 0, "mismatches": 0, "missing": 0}	\N	62	2026-06-30 16:58:07.753072-06	2026-06-30 16:58:07.753072-06
\N	service_order.quality_review	service_orders	2	{"status": "capture"}	{"status": "quality_review"}	\N	63	2026-06-30 16:58:20.741937-06	2026-06-30 16:58:20.741937-06
\N	service_order.updated	service_orders	2	{"technician_id": null, "agenda_date": null, "service_date": null, "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0002"}	{"technician_id": null, "agenda_date": null, "service_date": null, "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0002"}	\N	64	2026-06-30 16:58:23.276738-06	2026-06-30 16:58:23.276738-06
\N	equipment.labeled	equipment	2	{"status": "calibrated"}	{"status": "labeled"}	\N	65	2026-06-30 16:59:42.057316-06	2026-06-30 16:59:42.057316-06
\N	equipment.deactivated	equipment	2	{"is_active": true}	{"is_active": false, "status": "cancelled"}	\N	66	2026-06-30 17:00:16.608547-06	2026-06-30 17:00:16.608547-06
\N	service_order.deactivated	service_orders	2	{"is_active": true}	{"is_active": false}	\N	67	2026-06-30 17:00:40.505161-06	2026-06-30 17:00:40.505161-06
\N	service_order.created	service_orders	3	null	{"folio": "OSMYC-26-06-0003", "work_order_number": 7003, "client_id": 1, "quotation_id": 2, "status": "scheduled"}	\N	68	2026-06-30 17:00:49.853128-06	2026-06-30 17:00:49.853128-06
\N	service_order.updated	service_orders	3	{"technician_id": null, "agenda_date": null, "service_date": null, "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0002"}	{"technician_id": 1, "agenda_date": "2026-06-23", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0002"}	\N	69	2026-06-30 17:01:21.374908-06	2026-06-30 17:01:21.374908-06
\N	service_order.confirmed	service_orders	3	{"status": "scheduled"}	{"status": "confirmed"}	\N	70	2026-06-30 17:01:23.455781-06	2026-06-30 17:01:23.455781-06
\N	equipment.created	equipment	3	null	{"service_order_id": 3, "name": "IENVINWEI|PIBFIWB", "status": "registered"}	\N	71	2026-06-30 17:01:47.51028-06	2026-06-30 17:01:47.51028-06
\N	equipment.created	equipment	4	null	{"service_order_id": 3, "name": "EPFIVNWPIEVN", "status": "registered"}	\N	72	2026-06-30 17:02:05.404049-06	2026-06-30 17:02:05.404049-06
\N	equipment.realizing	equipment	4	{"status": "registered"}	{"status": "realizing"}	\N	73	2026-06-30 17:02:10.873471-06	2026-06-30 17:02:10.873471-06
\N	equipment.realizing	equipment	3	{"status": "registered"}	{"status": "realizing"}	\N	74	2026-06-30 17:02:14.021964-06	2026-06-30 17:02:14.021964-06
\N	field_sheet.created	field_sheets	3	null	{"equipment_id": 4, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "draft", "calibration_place": null, "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 21, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 22, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 23, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 24, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 25, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 26, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 27, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 28, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 29, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 30, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	75	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
\N	field_sheet.procedure_assigned	field_sheets	3	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	76	2026-06-30 17:03:02.459619-06	2026-06-30 17:03:02.459619-06
\N	field_sheet.created	field_sheets	4	null	{"equipment_id": 3, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "draft", "calibration_place": null, "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 31, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 32, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 33, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 34, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 35, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 36, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 37, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 38, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 39, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 40, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	85	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
\N	service_order.updated	service_orders	3	{"technician_id": 1, "agenda_date": "2026-06-23", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0002"}	{"technician_id": 1, "agenda_date": "2026-06-23", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0002"}	\N	97	2026-06-30 17:04:46.247893-06	2026-06-30 17:04:46.247893-06
\N	field_sheet.updated	field_sheets	3	{"equipment_id": 4, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "draft", "calibration_place": null, "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 21, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 22, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 23, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 24, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 25, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 26, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 27, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 28, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 29, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 30, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 4, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "in_progress", "calibration_place": "MYC", "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": true, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "OK", "final_condition": "OK", "pattern_used": null, "results": null, "observations": "OK", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 21, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "G", "notes": null}, {"id": 22, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 23, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 24, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 25, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 26, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 27, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 28, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 29, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 30, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	77	2026-06-30 17:03:02.459619-06	2026-06-30 17:03:02.459619-06
\N	field_sheet.procedure_assigned	field_sheets	3	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	78	2026-06-30 17:03:05.154349-06	2026-06-30 17:03:05.154349-06
\N	field_sheet.updated	field_sheets	3	{"equipment_id": 4, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "in_progress", "calibration_place": "MYC", "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": true, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "OK", "final_condition": "OK", "pattern_used": null, "results": null, "observations": "OK", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 21, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "G", "notes": null}, {"id": 22, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 23, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 24, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 25, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 26, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 27, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 28, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 29, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 30, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 4, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "in_progress", "calibration_place": "MYC", "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": true, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "OK", "final_condition": "OK", "pattern_used": null, "results": null, "observations": "OK", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 21, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "G", "notes": null}, {"id": 22, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 23, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 24, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 25, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 26, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 27, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 28, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 29, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 30, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	79	2026-06-30 17:03:05.154349-06	2026-06-30 17:03:05.154349-06
\N	field_sheet.procedure_assigned	field_sheets	3	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	80	2026-06-30 17:03:11.988804-06	2026-06-30 17:03:11.988804-06
\N	field_sheet.updated	field_sheets	3	{"equipment_id": 4, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "in_progress", "calibration_place": "MYC", "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": true, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "OK", "final_condition": "OK", "pattern_used": null, "results": null, "observations": "OK", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 21, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "G", "notes": null}, {"id": 22, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 23, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 24, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 25, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 26, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 27, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 28, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 29, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 30, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 4, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "in_progress", "calibration_place": "MYC", "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": true, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "OK", "final_condition": "OK", "pattern_used": null, "results": null, "observations": "OK", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 21, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "G", "notes": null}, {"id": 22, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 23, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 24, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 25, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 26, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 27, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 28, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 29, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 30, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	81	2026-06-30 17:03:11.988804-06	2026-06-30 17:03:11.988804-06
\N	field_sheet.completed	field_sheets	3	{"status": "in_progress", "equipment_status": "realizing"}	{"status": "completed", "equipment_status": "calibrated", "certificate_ready": true, "external_certificate_flow": true, "certificate_id": null, "certificate_status": null}	\N	82	2026-06-30 17:03:12.023175-06	2026-06-30 17:03:12.023175-06
\N	field_sheet.reviewed	field_sheets	3	{"status": "completed"}	{"status": "under_review", "certificate_id": null, "certificate_status": null}	\N	83	2026-06-30 17:03:13.305866-06	2026-06-30 17:03:13.305866-06
\N	equipment.labeled	equipment	4	{"status": "calibrated"}	{"status": "labeled"}	\N	84	2026-06-30 17:03:27.975879-06	2026-06-30 17:03:27.975879-06
\N	field_sheet.procedure_assigned	field_sheets	4	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	86	2026-06-30 17:03:59.582084-06	2026-06-30 17:03:59.582084-06
\N	field_sheet.updated	field_sheets	4	{"equipment_id": 3, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "draft", "calibration_place": null, "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 31, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 32, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 33, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 34, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 35, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 36, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 37, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 38, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 39, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 40, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 3, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "in_progress", "calibration_place": null, "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "OK", "final_condition": "OK", "pattern_used": null, "results": null, "observations": "OK", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 31, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 32, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 33, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 34, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 35, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 36, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 37, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 38, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 39, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 40, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	87	2026-06-30 17:03:59.582084-06	2026-06-30 17:03:59.582084-06
\N	field_sheet.procedure_assigned	field_sheets	4	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	88	2026-06-30 17:04:00.430129-06	2026-06-30 17:04:00.430129-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	132	2026-06-30 17:23:38.281631-06	2026-06-30 17:23:38.281631-06
\N	field_sheet.updated	field_sheets	4	{"equipment_id": 3, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "in_progress", "calibration_place": null, "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "OK", "final_condition": "OK", "pattern_used": null, "results": null, "observations": "OK", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 31, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 32, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 33, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 34, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 35, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 36, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 37, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 38, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 39, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 40, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 3, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7003, "status": "in_progress", "calibration_place": null, "reception_date": "2026-06-23", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0002", "initial_condition": "OK", "final_condition": "OK", "pattern_used": null, "results": null, "observations": "OK", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 31, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 32, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 33, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 34, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 35, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 36, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 37, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 38, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 39, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 40, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	89	2026-06-30 17:04:00.430129-06	2026-06-30 17:04:00.430129-06
\N	field_sheet.completed	field_sheets	4	{"status": "in_progress", "equipment_status": "realizing"}	{"status": "completed", "equipment_status": "calibrated", "certificate_ready": true, "external_certificate_flow": true, "certificate_id": null, "certificate_status": null}	\N	90	2026-06-30 17:04:00.464023-06	2026-06-30 17:04:00.464023-06
\N	field_sheet.reviewed	field_sheets	4	{"status": "completed"}	{"status": "under_review", "certificate_id": null, "certificate_status": null}	\N	91	2026-06-30 17:04:01.348435-06	2026-06-30 17:04:01.348435-06
\N	equipment.labeled	equipment	3	{"status": "calibrated"}	{"status": "labeled"}	\N	92	2026-06-30 17:04:07.79863-06	2026-06-30 17:04:07.79863-06
\N	certificate.bulk_pdf_upload	service_orders	3	null	{"service_order_id": 3, "expected": 0, "uploaded": 2, "matched": 0, "warnings": 0, "mismatches": 0, "missing": 0}	\N	93	2026-06-30 17:04:24.930641-06	2026-06-30 17:04:24.930641-06
\N	service_order.called	service_orders	3	{"status": "confirmed"}	{"status": "called"}	\N	94	2026-06-30 17:04:40.758495-06	2026-06-30 17:04:40.758495-06
\N	service_order.in_progress	service_orders	3	{"status": "called"}	{"status": "in_progress"}	\N	95	2026-06-30 17:04:42.249135-06	2026-06-30 17:04:42.249135-06
\N	service_order.capture	service_orders	3	{"status": "in_progress"}	{"status": "capture"}	\N	96	2026-06-30 17:04:43.807493-06	2026-06-30 17:04:43.807493-06
\N	certificate.bulk_pdf_upload	service_orders	3	null	{"service_order_id": 3, "expected": 0, "uploaded": 2, "matched": 0, "warnings": 0, "mismatches": 0, "missing": 0}	\N	98	2026-06-30 17:05:29.907129-06	2026-06-30 17:05:29.907129-06
\N	quotation.deactivated	quotations	2	{"is_active": true}	{"is_active": false}	\N	99	2026-06-30 17:06:20.897867-06	2026-06-30 17:06:20.897867-06
\N	service_order.deactivated	service_orders	3	{"is_active": true}	{"is_active": false}	\N	100	2026-06-30 17:06:26.997425-06	2026-06-30 17:06:26.997425-06
\N	quotation.created	quotations	3	null	{"folio": "MYC-06-26-0003", "client_id": 1, "total": "0.00"}	\N	101	2026-06-30 17:18:59.266703-06	2026-06-30 17:18:59.266703-06
\N	quotation.updated	quotations	3	{"valid_until": null, "notes": null}	{"valid_until": "2026-07-11", "notes": null}	\N	102	2026-06-30 17:19:06.040635-06	2026-06-30 17:19:06.040635-06
\N	quotation.item_added	quotations	3	null	{"service_name": "Servicio de calibraci\\u00f3n a b\\u00e1scula", "quantity": 1, "total": "1200.00"}	\N	103	2026-06-30 17:19:12.95067-06	2026-06-30 17:19:12.95067-06
\N	quotation.sent	quotations	3	{"status": "draft"}	{"status": "sent"}	\N	104	2026-06-30 17:19:18.965998-06	2026-06-30 17:19:18.965998-06
\N	quotation.waiting	quotations	3	{"status": "sent"}	{"status": "waiting"}	\N	105	2026-06-30 17:19:22.477214-06	2026-06-30 17:19:22.477214-06
\N	quotation.accepted	quotations	3	{"status": "waiting"}	{"status": "accepted"}	\N	106	2026-06-30 17:19:24.443069-06	2026-06-30 17:19:24.443069-06
\N	service_order.created	service_orders	4	null	{"folio": "OSMYC-26-06-0004", "work_order_number": 7004, "client_id": 1, "quotation_id": 3, "status": "scheduled"}	\N	107	2026-06-30 17:19:28.200981-06	2026-06-30 17:19:28.200981-06
\N	service_order.confirmed	service_orders	4	{"status": "scheduled"}	{"status": "confirmed"}	\N	108	2026-06-30 17:21:11.04886-06	2026-06-30 17:21:11.04886-06
\N	service_order.called	service_orders	4	{"status": "confirmed"}	{"status": "called"}	\N	109	2026-06-30 17:21:12.386148-06	2026-06-30 17:21:12.386148-06
\N	equipment.created	equipment	5	null	{"service_order_id": 4, "name": "vevdfv", "status": "registered"}	\N	110	2026-06-30 17:21:25.153481-06	2026-06-30 17:21:25.153481-06
\N	service_order.updated	service_orders	4	{"technician_id": null, "agenda_date": null, "service_date": null, "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	\N	111	2026-06-30 17:21:49.19047-06	2026-06-30 17:21:49.19047-06
\N	service_order.in_progress	service_orders	4	{"status": "called"}	{"status": "in_progress"}	\N	112	2026-06-30 17:22:10.50552-06	2026-06-30 17:22:10.50552-06
\N	equipment.realizing	equipment	5	{"status": "registered"}	{"status": "realizing"}	\N	113	2026-06-30 17:22:31.761253-06	2026-06-30 17:22:31.761253-06
\N	field_sheet.created	field_sheets	5	null	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "draft", "calibration_place": null, "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	114	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
1	pattern_selection.candidates_generated	pattern_selection	\N	null	{"technical_profile_id": null, "magnitude": "unknown", "range_min": 0.0, "range_max": 100.0, "candidates": 0, "recommendations": []}	\N	115	2026-06-30 17:22:54.290229-06	2026-06-30 17:22:54.290229-06
1	field_sheet.patterns_validated	field_sheets	5	null	{"selected_pattern_ids": [], "errors": ["No hay patrones validos para el contexto indicado."], "warnings": []}	\N	116	2026-06-30 17:22:56.603156-06	2026-06-30 17:22:56.603156-06
1	field_sheet.patterns_validated	field_sheets	5	null	{"selected_pattern_ids": [], "errors": ["No hay patrones validos para el contexto indicado."], "warnings": []}	\N	117	2026-06-30 17:22:57.30079-06	2026-06-30 17:22:57.30079-06
1	field_sheet.patterns_validated	field_sheets	5	null	{"selected_pattern_ids": [], "errors": ["No hay patrones validos para el contexto indicado."], "warnings": []}	\N	118	2026-06-30 17:22:57.800889-06	2026-06-30 17:22:57.800889-06
1	pattern_selection.candidates_generated	pattern_selection	\N	null	{"technical_profile_id": null, "magnitude": "unknown", "range_min": 0.0, "range_max": 100.0, "candidates": 0, "recommendations": []}	\N	119	2026-06-30 17:22:58.416863-06	2026-06-30 17:22:58.416863-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	120	2026-06-30 17:23:31.154629-06	2026-06-30 17:23:31.154629-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	122	2026-06-30 17:23:32.416301-06	2026-06-30 17:23:32.416301-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "draft", "calibration_place": null, "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	121	2026-06-30 17:23:31.154629-06	2026-06-30 17:23:31.154629-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	123	2026-06-30 17:23:32.416301-06	2026-06-30 17:23:32.416301-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	124	2026-06-30 17:23:37.684995-06	2026-06-30 17:23:37.684995-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	125	2026-06-30 17:23:37.684995-06	2026-06-30 17:23:37.684995-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	128	2026-06-30 17:23:37.998257-06	2026-06-30 17:23:37.998257-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	129	2026-06-30 17:23:37.998257-06	2026-06-30 17:23:37.998257-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	130	2026-06-30 17:23:38.130355-06	2026-06-30 17:23:38.130355-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	131	2026-06-30 17:23:38.130355-06	2026-06-30 17:23:38.130355-06
\N	service_order.updated	service_orders	4	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	\N	149	2026-06-30 17:25:14.903074-06	2026-06-30 17:25:14.903074-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	127	2026-06-30 17:23:37.830697-06	2026-06-30 17:23:37.830697-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	133	2026-06-30 17:23:38.281631-06	2026-06-30 17:23:38.281631-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	134	2026-06-30 17:23:38.433555-06	2026-06-30 17:23:38.433555-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	135	2026-06-30 17:23:38.433555-06	2026-06-30 17:23:38.433555-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	136	2026-06-30 17:23:38.580908-06	2026-06-30 17:23:38.580908-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	137	2026-06-30 17:23:38.580908-06	2026-06-30 17:23:38.580908-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	138	2026-06-30 17:23:38.733736-06	2026-06-30 17:23:38.733736-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	139	2026-06-30 17:23:38.733736-06	2026-06-30 17:23:38.733736-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	140	2026-06-30 17:23:38.880785-06	2026-06-30 17:23:38.880785-06
\N	field_sheet.reviewed	field_sheets	5	{"status": "completed"}	{"status": "under_review", "certificate_id": null, "certificate_status": null}	\N	145	2026-06-30 17:23:46.686908-06	2026-06-30 17:23:46.686908-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	141	2026-06-30 17:23:38.880785-06	2026-06-30 17:23:38.880785-06
\N	field_sheet.procedure_assigned	field_sheets	5	{"calibration_procedure_id": null}	{"calibration_procedure_id": null}	\N	142	2026-06-30 17:23:45.41829-06	2026-06-30 17:23:45.41829-06
\N	field_sheet.updated	field_sheets	5	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	{"equipment_id": 5, "calibration_procedure_id": null, "template_key": "general", "work_order_number": 7004, "status": "in_progress", "calibration_place": "myc", "reception_date": "2026-07-02", "calibration_date": "2026-07-01", "next_calibration_date": "2027-07-01", "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": "miguel", "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-06-26-0003", "initial_condition": "ok", "final_condition": "ok", "pattern_used": null, "results": null, "observations": "ok", "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "results_rows": [{"id": 41, "section_key": "main", "row_number": 1, "pattern_value": "40", "ibc_value_1": "39", "ibc_value_2": "39", "ibc_value_3": "39", "unit": "KG", "notes": null}, {"id": 42, "section_key": "main", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 43, "section_key": "main", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 44, "section_key": "main", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 45, "section_key": "main", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 46, "section_key": "main", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 47, "section_key": "main", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 48, "section_key": "main", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 49, "section_key": "main", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}, {"id": 50, "section_key": "main", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null}], "reference_standards": []}	\N	143	2026-06-30 17:23:45.41829-06	2026-06-30 17:23:45.41829-06
\N	field_sheet.completed	field_sheets	5	{"status": "in_progress", "equipment_status": "realizing"}	{"status": "completed", "equipment_status": "calibrated", "certificate_ready": true, "external_certificate_flow": true, "certificate_id": null, "certificate_status": null}	\N	144	2026-06-30 17:23:45.462923-06	2026-06-30 17:23:45.462923-06
\N	certificate.bulk_pdf_upload	service_orders	4	null	{"service_order_id": 4, "expected": 0, "uploaded": 1, "matched": 0, "warnings": 0, "mismatches": 0, "missing": 0}	\N	146	2026-06-30 17:23:57.74189-06	2026-06-30 17:23:57.74189-06
\N	certificate.bulk_pdf_upload	service_orders	4	null	{"service_order_id": 4, "expected": 0, "uploaded": 1, "matched": 0, "warnings": 0, "mismatches": 0, "missing": 0}	\N	147	2026-06-30 17:24:25.300997-06	2026-06-30 17:24:25.300997-06
\N	certificate.bulk_pdf_upload	service_orders	4	null	{"service_order_id": 4, "expected": 0, "uploaded": 1, "matched": 0, "warnings": 0, "mismatches": 0, "missing": 0}	\N	148	2026-06-30 17:24:39.936723-06	2026-06-30 17:24:39.936723-06
\N	service_order.updated	service_orders	4	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	\N	150	2026-06-30 17:25:15.251708-06	2026-06-30 17:25:15.251708-06
\N	service_order.updated	service_orders	4	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	\N	151	2026-06-30 17:25:15.398758-06	2026-06-30 17:25:15.398758-06
\N	service_order.updated	service_orders	4	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	\N	152	2026-06-30 17:25:15.517359-06	2026-06-30 17:25:15.517359-06
\N	service_order.updated	service_orders	4	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	\N	153	2026-06-30 17:25:15.666008-06	2026-06-30 17:25:15.666008-06
\N	service_order.updated	service_orders	4	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	{"technician_id": 1, "agenda_date": "2026-07-02", "service_date": "2026-07-01", "requires_payment": true, "notes": "Generada desde cotizacion MYC-06-26-0003"}	\N	154	2026-06-30 17:25:15.804744-06	2026-06-30 17:25:15.804744-06
\N	service_order.capture	service_orders	4	{"status": "in_progress"}	{"status": "capture"}	\N	155	2026-06-30 17:25:16.75519-06	2026-06-30 17:25:16.75519-06
\N	service_order.quality_review	service_orders	4	{"status": "capture"}	{"status": "quality_review"}	\N	156	2026-06-30 17:25:18.642551-06	2026-06-30 17:25:18.642551-06
\N	certificate.expected_created	certificates	2	null	{"folio": "MYCT-06-2026-0002", "expected_folio": "MYCT-06-2026-0002", "service_order_id": 4, "equipment_id": 5, "field_sheet_id": 5, "status": "expected"}	\N	157	2026-06-30 17:26:42.903093-06	2026-06-30 17:26:42.903093-06
\.


--
-- Data for Name: calibration_procedures; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.calibration_procedures (code, name, description, magnitude, profile_key, version, issuer_company, certificate_type, required_readings, decision_rule, acceptance_criteria, notes, status, is_active, deleted_at, deleted_by, id, created_at, updated_at, uncertainty_model_id, uncertainty_model_version_id) FROM stdin;
\.


--
-- Data for Name: catalog_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.catalog_items (item_type, commodity, category, internal_key, name, description, sat_key, sat_unit, internal_unit, origin_price, origin_currency, exchange_rate, margin_percent, final_price_mxn, internal_cost, cost_currency, calibration_scope, quotation_legend, id, created_at, updated_at, is_active, deleted_at, deleted_by, custom_internal_unit, tax_object, tax_rate) FROM stdin;
service	calibration	Calibracion	SER-CAL-0001	Servicio de calibración a báscula	\N	81141504	E48	service	1200.00	MXN	1.000000	0.0000	1200.00	\N	\N	accredited_iso_17025	Servicio acreditado ISO/IEC 17025:2017	1	2026-06-30 13:14:57.000475-06	2026-06-30 13:14:57.000475-06	t	\N	\N	\N	iva_16	16.00
\.


--
-- Data for Name: certificates; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.certificates (folio, service_order_id, equipment_id, field_sheet_id, certificate_type, status, issued_on, released_on, title, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, expected_folio, final_pdf_path, final_pdf_original_filename, final_pdf_uploaded_at, final_pdf_uploaded_by_id, capture_started_at, capture_started_by_id, sent_to_quality_at, sent_to_quality_by_id, quality_reviewed_at, quality_reviewed_by_id, quality_rejection_reason, released_to_client_at, released_to_client_by_id, external_source, match_status, match_details, client_visible, authentication_code, authentication_hash, authenticated_pdf_path, authenticated_pdf_generated_at, authenticated_by_id, verification_url) FROM stdin;
MYCT-06-2026-0001	1	1	1	trazable	released_to_client	2026-06-30	2026-06-30	\N	\N	1	2026-06-30 15:07:04.089481-06	2026-06-30 15:07:29.485351-06	t	\N	\N	MYCT-06-2026-0001	/Users/saulcortes/Desktop/myc_erp/storage/certificados/7001/MYCT-06-2026-0001_MYCA-01-26-3281_TERMOMETRO_DE_CARATULA_TE-NBF-10_PROX_CAL_2027-01-26.pdf	MYCA-01-26-3281 TERMOMETRO DE CARATULA TE-NBF-10 PROX CAL 2027-01-26.pdf	2026-06-30 15:07:17.672136-06	\N	2026-06-30 15:07:12.829689-06	\N	2026-06-30 15:07:21.26331-06	\N	2026-06-30 15:07:26.178129-06	\N	\N	2026-06-30 15:07:29.489256-06	\N	excel	manual_accepted	{"status": "mismatch", "score": 0, "filename": "MYCA-01-26-3281 TERMOMETRO DE CARATULA TE-NBF-10 PROX CAL 2027-01-26.pdf", "checks": [{"field": "folio", "expected": "MYCT-06-2026-0001", "found": null, "status": "mismatch", "weight": 45}, {"field": "serial_number", "expected": "234253242", "found": null, "status": "mismatch", "weight": 20}, {"field": "internal_id", "expected": "bas-30", "found": null, "status": "mismatch", "weight": 15}, {"field": "equipment_name", "expected": "b\\u00e1scula", "found": null, "status": "mismatch", "weight": 10}, {"field": "work_order_number", "expected": "7001", "found": null, "status": "mismatch", "weight": 10}], "warnings": [], "errors": ["El archivo no coincide con el folio/equipo esperado."]}	t	MYC-AUTH-2026-000001	074f6f2c3e97c4dc84985580d389edc9b12ad86a74687af78df5eafceec443db	/Users/saulcortes/Desktop/myc_erp/storage/certificados/7001/MYCT-06-2026-0001_MYCA-01-26-3281_TERMOMETRO_DE_CARATULA_TE-NBF-10_PROX_CAL_2027-01-26_autenticado_MYC-AUTH-2026-000001.pdf	2026-06-30 15:07:29.489372-06	\N	https://api-erp.mycmetrology.com.mx/verify/MYC-AUTH-2026-000001
MYCT-06-2026-0002	4	5	5	trazable	expected	2026-06-30	\N	\N	\N	2	2026-06-30 17:26:42.903093-06	2026-06-30 17:26:42.903093-06	t	\N	\N	MYCT-06-2026-0002	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	excel	pending	\N	f	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: client_contacts; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.client_contacts (client_id, name, email, phone, "position", id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
1	PRUEBA CORTES	prueba@myc.com	3093093029	\N	1	2026-06-30 13:08:02.939115-06	2026-06-30 13:08:02.939115-06	t	\N	\N
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.clients (legal_name, commercial_name, rfc, email, phone, tax_regime, payment_terms, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
prueba	PRUEBA	FIWUENFIOUWN	prueba@myc.com	3093093029	\N	\N	\N	1	2026-06-30 13:08:02.939115-06	2026-06-30 13:08:02.939115-06	t	\N	\N
\.


--
-- Data for Name: controlled_document_versions; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.controlled_document_versions (document_id, revision, file_path, original_filename, mime_type, checksum, change_summary, uploaded_by_id, approved_by_id, reviewed_by_id, status, effective_date, uploaded_at, approved_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: controlled_documents; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.controlled_documents (code, name, document_type, quality_level, current_revision, issue_date, last_review_date, effective_date, retention_time, digital_location, status, description, created_by_id, id, created_at, updated_at) FROM stdin;
MDG-01	Manual de Gestion de la Calidad	manual	Nivel I	\N	\N	\N	\N	\N	\N	draft	Documento semilla del nucleo documental.	\N	1	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06
FCA-02	Lista Maestra de Documentos	record	Nivel II	\N	\N	\N	\N	\N	\N	draft	Lista maestra inicial.	\N	2	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06
PMP-01	Procedimiento de uso y calibracion de manometros y vacuometros	procedure	Nivel II	\N	\N	\N	\N	\N	\N	draft	Procedimiento base para presion.	\N	3	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06
FCA-15-7	Calibracion de manometros	field_sheet_template	Nivel III	\N	\N	\N	\N	\N	\N	draft	Formato semilla de hoja de campo.	\N	4	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06
FPV-01	Orden de trabajo	work_order_template	Nivel III	\N	\N	\N	\N	\N	\N	draft	Formato semilla de orden de trabajo.	\N	5	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06
FCA-22	Cotizacion	quotation_template	Nivel III	\N	\N	\N	\N	\N	\N	draft	Formato semilla de cotizacion.	\N	6	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06
FCA-18-1	Calculo de incertidumbre	uncertainty_calculation	Nivel III	\N	\N	\N	\N	\N	\N	draft	Fuente documental para modelo de incertidumbre futuro.	\N	7	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06
\.


--
-- Data for Name: document_interpretations; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.document_interpretations (document_id, document_version_id, name, interpretation_type, magnitude, equipment_type, service_type, calibration_scope, data, status, version, created_by_id, approved_by_id, approved_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: document_templates; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.document_templates (template_key, name, company_name, company_tagline, company_rfc, company_email, company_website, company_address, company_phone, document_title, document_subtitle, document_code, document_revision, document_issued_on, terms_version, commercial_terms, metrological_terms, legal_terms, privacy_notice, acceptance_text, show_summary_terms, show_full_terms, show_acceptance_signature, is_active, id, created_at, updated_at) FROM stdin;
quotation	Plantilla de cotizacion MYC	Metrologia y Servicios MYC	Servicios de metrologia, calibracion, venta y soporte tecnico especializado.	MYC000000XXX	contacto@mycmetrology.com.mx	www.mycmetrology.com.mx			COTIZACION	Propuesta comercial de servicios, calibracion y soluciones tecnicas	FCA-23-2	\N	2025-03-28	V1	Precios expresados en moneda nacional, salvo indicacion contraria.\nVigencia sujeta a la fecha indicada en esta cotizacion.\nTiempos de entrega y alcance final se confirman al recibir autorizacion.	Los servicios metrologicos se ejecutan conforme al alcance tecnico autorizado y a la disponibilidad de patrones aplicables.	La autorizacion de esta cotizacion implica aceptacion de las condiciones comerciales, tecnicas y documentales descritas.	Los datos del cliente se usan exclusivamente para fines comerciales, operativos, documentales y de facturacion relacionados con el servicio solicitado.	Acepto las condiciones comerciales, metrologicas y legales de la presente cotizacion.	t	t	t	t	1	2026-06-30 13:08:06.941653-06	2026-06-30 13:08:06.941653-06
\.


--
-- Data for Name: equipment; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.equipment (service_order_id, service_order_item_id, status, name, brand, model, serial_number, internal_id, range_or_capacity, initial_condition, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
1	\N	labeled	báscula	ohau	ohaus	234253242	bas-30	0 - 1200 g	on	Buen estado	1	2026-06-30 13:20:14.879019-06	2026-06-30 15:09:34.826942-06	t	\N	\N
2	\N	cancelled	ewfwefewf	revrev	wverv	3rgerv	erverv	0-200 kg	\N	\N	2	2026-06-30 16:51:42.392329-06	2026-06-30 17:00:16.608547-06	f	2026-06-30 17:00:16.611315-06	\N
3	\N	labeled	EPFIVNWPIEVN	WNEROVN	IENFVOWEN	VPIURNEWIN	OIUNOUBNU	0 - 90	\N	\N	4	2026-06-30 17:02:05.404049-06	2026-06-30 17:03:27.975879-06	t	\N	\N
3	\N	labeled	IENVINWEI|PIBFIWB	OINFOBN	PIUBNOUB	OHIBOUHBB	OHBOUHB	0 -100	\N	\N	3	2026-06-30 17:01:47.51028-06	2026-06-30 17:04:07.79863-06	t	\N	\N
4	\N	calibrated	vevdfv	kjnkjnkj	kjnkjn	kjnkjn	knkjn	0-100	\N	\N	5	2026-06-30 17:21:25.153481-06	2026-06-30 17:23:45.462923-06	t	\N	\N
\.


--
-- Data for Name: field_sheet_reference_standards; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheet_reference_standards (field_sheet_id, reference_standard_id, usage_role, measurement_section, notes, id, created_at, updated_at, reference_standard_certificate_id, selected_uncertainty_id, selection_status, selection_notes, validation_snapshot) FROM stdin;
\.


--
-- Data for Name: field_sheet_results; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheet_results (field_sheet_id, section_key, row_number, pattern_value, ibc_value_1, ibc_value_2, ibc_value_3, unit, notes, id, created_at, updated_at) FROM stdin;
1	main	2	\N	\N	\N	\N	\N	\N	2	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
1	main	3	\N	\N	\N	\N	\N	\N	3	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
1	main	4	\N	\N	\N	\N	\N	\N	4	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
1	main	5	\N	\N	\N	\N	\N	\N	5	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
1	main	6	\N	\N	\N	\N	\N	\N	6	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
1	main	7	\N	\N	\N	\N	\N	\N	7	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
1	main	8	\N	\N	\N	\N	\N	\N	8	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
1	main	9	\N	\N	\N	\N	\N	\N	9	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
1	main	10	\N	\N	\N	\N	\N	\N	10	2026-06-30 13:24:18.04799-06	2026-06-30 13:24:18.04799-06
1	main	1	323	43	34	43	g	\N	1	2026-06-30 13:24:18.04799-06	2026-06-30 13:31:07.09876-06
2	main	2	\N	\N	\N	\N	\N	\N	12	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
2	main	3	\N	\N	\N	\N	\N	\N	13	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
2	main	4	\N	\N	\N	\N	\N	\N	14	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
2	main	5	\N	\N	\N	\N	\N	\N	15	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
2	main	6	\N	\N	\N	\N	\N	\N	16	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
2	main	7	\N	\N	\N	\N	\N	\N	17	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
2	main	8	\N	\N	\N	\N	\N	\N	18	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
2	main	9	\N	\N	\N	\N	\N	\N	19	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
2	main	10	\N	\N	\N	\N	\N	\N	20	2026-06-30 16:51:47.439715-06	2026-06-30 16:51:47.439715-06
2	main	1	40	4039	2094	320	kg	\N	11	2026-06-30 16:51:47.439715-06	2026-06-30 16:52:22.258667-06
3	main	2	\N	\N	\N	\N	\N	\N	22	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
3	main	3	\N	\N	\N	\N	\N	\N	23	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
3	main	4	\N	\N	\N	\N	\N	\N	24	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
3	main	5	\N	\N	\N	\N	\N	\N	25	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
3	main	6	\N	\N	\N	\N	\N	\N	26	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
3	main	7	\N	\N	\N	\N	\N	\N	27	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
3	main	8	\N	\N	\N	\N	\N	\N	28	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
3	main	9	\N	\N	\N	\N	\N	\N	29	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
3	main	10	\N	\N	\N	\N	\N	\N	30	2026-06-30 17:02:17.270365-06	2026-06-30 17:02:17.270365-06
3	main	1	40	39	39	39	G	\N	21	2026-06-30 17:02:17.270365-06	2026-06-30 17:03:02.459619-06
4	main	2	\N	\N	\N	\N	\N	\N	32	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
4	main	3	\N	\N	\N	\N	\N	\N	33	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
4	main	4	\N	\N	\N	\N	\N	\N	34	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
4	main	5	\N	\N	\N	\N	\N	\N	35	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
4	main	6	\N	\N	\N	\N	\N	\N	36	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
4	main	7	\N	\N	\N	\N	\N	\N	37	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
4	main	8	\N	\N	\N	\N	\N	\N	38	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
4	main	9	\N	\N	\N	\N	\N	\N	39	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
4	main	10	\N	\N	\N	\N	\N	\N	40	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:34.127457-06
4	main	1	40	39	39	39	KG	\N	31	2026-06-30 17:03:34.127457-06	2026-06-30 17:03:59.582084-06
5	main	2	\N	\N	\N	\N	\N	\N	42	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
5	main	3	\N	\N	\N	\N	\N	\N	43	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
5	main	4	\N	\N	\N	\N	\N	\N	44	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
5	main	5	\N	\N	\N	\N	\N	\N	45	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
5	main	6	\N	\N	\N	\N	\N	\N	46	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
5	main	7	\N	\N	\N	\N	\N	\N	47	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
5	main	8	\N	\N	\N	\N	\N	\N	48	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
5	main	9	\N	\N	\N	\N	\N	\N	49	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
5	main	10	\N	\N	\N	\N	\N	\N	50	2026-06-30 17:22:46.17154-06	2026-06-30 17:22:46.17154-06
5	main	1	40	39	39	39	KG	\N	41	2026-06-30 17:22:46.17154-06	2026-06-30 17:23:31.154629-06
\.


--
-- Data for Name: field_sheets; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheets (equipment_id, status, initial_condition, final_condition, pattern_used, results, observations, evidence_notes, method, environmental_conditions, technician_notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, template_key, work_order_number, calibration_place, reception_date, calibration_date, next_calibration_date, environment_humidity_start, environment_humidity_end, environment_temperature_start, environment_temperature_end, equipment_general_condition, consider_equipment_deviations, units, calibrated_by, reviewed_by, report_made_by, purchase_order_or_quotation, calibration_procedure_id, returned_to_technician_at, returned_to_technician_by_id, returned_to_technician_reason) FROM stdin;
1	under_review	ok	ok	\N	\N	buen estado	\N	\N	ok	\N	1	2026-06-30 13:24:18.04799-06	2026-06-30 13:31:44.746784-06	t	\N	\N	general	7001	lab myc	2026-06-30	2026-06-26	2027-06-30	32	23	32	32	t	f	g	miguel muñoz	\N	\N	MYC-06-26-0001	\N	\N	\N	\N
2	under_review	ok	ok	\N	\N	ok	\N	\N	\N	\N	2	2026-06-30 16:51:47.439715-06	2026-06-30 16:53:48.059354-06	t	\N	\N	general	7002	\N	2026-06-30	2026-07-02	2027-11-17	\N	\N	\N	\N	\N	f	\N	\N	\N	\N	MYC-06-26-0002	\N	\N	\N	\N
4	under_review	OK	OK	\N	\N	OK	\N	\N	\N	\N	3	2026-06-30 17:02:17.270365-06	2026-06-30 17:03:13.305866-06	t	\N	\N	general	7003	MYC	2026-06-23	2026-07-01	2027-07-01	\N	\N	\N	\N	t	f	\N	\N	\N	\N	MYC-06-26-0002	\N	\N	\N	\N
3	under_review	OK	OK	\N	\N	OK	\N	\N	\N	\N	4	2026-06-30 17:03:34.127457-06	2026-06-30 17:04:01.348435-06	t	\N	\N	general	7003	\N	2026-06-23	2026-07-01	2027-07-01	\N	\N	\N	\N	\N	f	\N	\N	\N	\N	MYC-06-26-0002	\N	\N	\N	\N
5	under_review	ok	ok	\N	\N	ok	\N	\N	\N	\N	5	2026-06-30 17:22:46.17154-06	2026-06-30 17:23:46.686908-06	t	\N	\N	general	7004	myc	2026-07-02	2026-07-01	2027-07-01	\N	\N	\N	\N	\N	f	\N	miguel	\N	\N	MYC-06-26-0003	\N	\N	\N	\N
\.


--
-- Data for Name: quotation_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.quotation_items (quotation_id, service_name, description, quantity, unit_price, total, id, created_at, updated_at, is_active, deleted_at, deleted_by, catalog_item_id, unit, currency, commodity, calibration_scope, quotation_legend, sat_key, sat_unit, internal_unit, discount_percent, tax_object, tax_rate, tax_total) FROM stdin;
2	Servicio de calibración a báscula	\N	8	1200.00	9600.00	1	2026-06-30 16:50:17.871668-06	2026-06-30 16:50:17.871668-06	t	\N	\N	1	service	MXN	calibration	accredited_iso_17025	Servicio acreditado ISO/IEC 17025:2017	81141504	E48	service	0.0000	iva_16	16.00	1536.00
3	Servicio de calibración a báscula	\N	1	1200.00	1200.00	2	2026-06-30 17:19:12.95067-06	2026-06-30 17:19:12.95067-06	t	\N	\N	1	service	MXN	calibration	accredited_iso_17025	Servicio acreditado ISO/IEC 17025:2017	81141504	E48	service	0.0000	iva_16	16.00	192.00
\.


--
-- Data for Name: quotations; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.quotations (folio, client_id, status, issued_on, valid_until, subtotal, tax_total, total, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, advisor_id) FROM stdin;
MYC-06-26-0001	1	accepted	2026-06-30	2026-07-01	0.00	0.00	0.00	\N	1	2026-06-30 13:08:57.560275-06	2026-06-30 16:49:20.25349-06	f	2026-06-30 16:49:20.257487-06	\N	\N
MYC-06-26-0002	1	accepted	2026-06-30	2026-07-02	9600.00	1536.00	11136.00	\N	2	2026-06-30 16:49:44.274436-06	2026-06-30 17:06:20.897867-06	f	2026-06-30 17:06:20.900828-06	\N	\N
MYC-06-26-0003	1	accepted	2026-06-30	2026-07-11	1200.00	192.00	1392.00	\N	3	2026-06-30 17:18:59.266703-06	2026-06-30 17:19:24.443069-06	t	\N	\N	\N
\.


--
-- Data for Name: reference_standard_certificate_uncertainties; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.reference_standard_certificate_uncertainties (certificate_id, magnitude, measurement_type, range_min, range_max, unit, uncertainty_value, uncertainty_unit, k_factor, confidence_level, distribution, formula_reference, notes, is_active, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: reference_standard_certificates; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.reference_standard_certificates (reference_standard_id, controlled_document_id, controlled_document_version_id, certificate_number, issuing_laboratory, accreditation_body, accreditation_number, calibration_date, expiration_date, received_date, status, is_current, traceability_statement, environmental_conditions, notes, created_by_id, approved_by_id, approved_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: reference_standard_uncertainties; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.reference_standard_uncertainties (reference_standard_id, range_min, range_max, unit, uncertainty_value, coverage_factor_k, distribution, notes, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: reference_standards; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.reference_standards (internal_code, name, description, owner_company, magnitude, brand, model, serial_number, identification, unit, range_min, range_max, resolution, coverage_factor_k, provider, calibration_laboratory, certificate_number, certificate_file_path, calibrated_on, next_calibration_on, status, notes, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.roles (name, description, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
Administrador	Acceso total al sistema.	1	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06	t	\N	\N
Comercial	Gestion comercial, clientes y cotizaciones.	2	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06	t	\N	\N
Tecnico	Gestion tecnica de equipos y hojas de campo.	3	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06	t	\N	\N
Captura	Captura y generacion documental.	4	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06	t	\N	\N
Calidad	Revision y aprobacion de certificados.	5	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06	t	\N	\N
Finanzas	Pagos, facturacion y liberacion financiera.	6	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06	t	\N	\N
Cliente	Acceso limitado para cliente externo.	7	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06	t	\N	\N
Desarrollador	Acceso tecnico avanzado para desarrollo y soporte.	8	2026-06-30 12:50:53.013335-06	2026-06-30 12:50:53.013335-06	t	\N	\N
\.


--
-- Data for Name: service_order_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.service_order_items (service_order_id, quotation_item_id, service_name, quantity, status, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
2	1	Servicio de calibración a báscula	8	pending	1	2026-06-30 16:50:49.803401-06	2026-06-30 16:50:49.803401-06	t	\N	\N
3	1	Servicio de calibración a báscula	8	pending	2	2026-06-30 17:00:49.853128-06	2026-06-30 17:00:49.853128-06	t	\N	\N
4	2	Servicio de calibración a báscula	1	pending	3	2026-06-30 17:19:28.200981-06	2026-06-30 17:19:28.200981-06	t	\N	\N
\.


--
-- Data for Name: service_orders; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.service_orders (folio, client_id, quotation_id, status, agenda_date, closed_at, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, advisor_id, technician_id, service_date, total_equipment, completed_equipment, requires_payment, work_order_number) FROM stdin;
OSMYC-26-06-0001	1	1	released	\N	\N	Generada desde cotizacion MYC-06-26-0001	1	2026-06-30 13:16:48.34536-06	2026-06-30 16:49:27.67771-06	f	2026-06-30 16:49:27.69366-06	\N	\N	\N	\N	1	1	t	7001
OSMYC-26-06-0002	1	2	quality_review	\N	\N	Generada desde cotizacion MYC-06-26-0002	2	2026-06-30 16:50:49.803401-06	2026-06-30 17:00:40.505161-06	f	2026-06-30 17:00:40.52061-06	\N	\N	\N	\N	1	1	t	7002
OSMYC-26-06-0003	1	2	capture	2026-06-23	\N	Generada desde cotizacion MYC-06-26-0002	3	2026-06-30 17:00:49.853128-06	2026-06-30 17:06:26.997425-06	f	2026-06-30 17:06:27.007127-06	\N	\N	1	2026-07-01	2	2	t	7003
OSMYC-26-06-0004	1	3	quality_review	2026-07-02	\N	Generada desde cotizacion MYC-06-26-0003	4	2026-06-30 17:19:28.200981-06	2026-06-30 17:25:18.642551-06	t	\N	\N	\N	1	2026-07-01	1	0	t	7004
\.


--
-- Data for Name: technical_profile_allowed_patterns; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.technical_profile_allowed_patterns (technical_profile_id, pattern_id, pattern_code, min_range, max_range, unit, priority, is_preferred, notes, created_at, id) FROM stdin;
\.


--
-- Data for Name: technical_profiles; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.technical_profiles (code, name, magnitude, equipment_type, service_type, calibration_scope, procedure_document_id, procedure_interpretation_id, field_sheet_template_document_id, certificate_template_document_id, uncertainty_source_document_id, status, version, rules, notes, created_by_id, approved_by_id, approved_at, id, created_at, updated_at) FROM stdin;
PT-PRESION-MANOMETRO-ACR-001	Perfil Tecnico Presion - Manometros Acreditado	Presion	Manometro	calibration	accredited	\N	\N	\N	\N	\N	draft	1	\N	Perfil semilla; no contiene calculos metrologicos.	\N	\N	\N	1	2026-06-30 12:49:34.370535-06	2026-06-30 12:49:34.370535-06
\.


--
-- Data for Name: uncertainty_calculations; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_calculations (field_sheet_id, uncertainty_model_id, status, calculated_at, calculation_snapshot, input_snapshot, component_results, formula_results, warnings, errors, id, created_at, updated_at, uncertainty_model_version_id) FROM stdin;
\.


--
-- Data for Name: uncertainty_components; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_components (model_id, key, name, description, source_type, distribution, divisor, sensitivity_coefficient, value_expression, required, sort_order, metadata_json, id, created_at, updated_at, is_active, deleted_at, deleted_by, model_version_id) FROM stdin;
\.


--
-- Data for Name: uncertainty_formulas; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_formulas (model_id, key, name, expression, result_key, description, sort_order, is_active_formula, id, created_at, updated_at, model_version_id) FROM stdin;
\.


--
-- Data for Name: uncertainty_model_exceptions; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_model_exceptions (base_model_id, alternate_model_id, magnitude, equipment_type, equipment_model, procedure_id, profile_key, reason, authorized_by_id, authorized_at, status, id, created_at, updated_at, is_active, deleted_at, deleted_by, base_model_version_id, alternate_model_version_id) FROM stdin;
\.


--
-- Data for Name: uncertainty_model_versions; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_model_versions (model_id, version_number, status, change_summary, default_coverage_factor, submitted_at, submitted_by_id, approved_at, approved_by_id, obsolete_at, archived_at, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
\.


--
-- Data for Name: uncertainty_models; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_models (code, name, description, magnitude, equipment_family, version, status, default_coverage_factor, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
\.


--
-- Data for Name: user_roles; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.user_roles (user_id, role_id) FROM stdin;
1	1
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.users (email, full_name, hashed_password, role_id, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
saul@myc.com	admin	$pbkdf2-sha256$29000$gJDSOmcMgdBaixHCWKtVag$B9MPhc0hOst9odrndsUvpPcClqebHvmHl8OyD99YoFU	1	1	2026-06-30 12:50:53.013335-06	2026-06-30 12:50:53.013335-06	t	\N	\N
\.


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 157, true);


--
-- Name: calibration_procedures_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.calibration_procedures_id_seq', 1, false);


--
-- Name: catalog_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.catalog_items_id_seq', 1, true);


--
-- Name: certificates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.certificates_id_seq', 2, true);


--
-- Name: client_contacts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.client_contacts_id_seq', 1, true);


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.clients_id_seq', 1, true);


--
-- Name: controlled_document_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.controlled_document_versions_id_seq', 1, false);


--
-- Name: controlled_documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.controlled_documents_id_seq', 7, true);


--
-- Name: document_interpretations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.document_interpretations_id_seq', 1, false);


--
-- Name: document_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.document_templates_id_seq', 1, true);


--
-- Name: equipment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.equipment_id_seq', 5, true);


--
-- Name: field_sheet_reference_standards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheet_reference_standards_id_seq', 1, false);


--
-- Name: field_sheet_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheet_results_id_seq', 50, true);


--
-- Name: field_sheets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheets_id_seq', 5, true);


--
-- Name: quotation_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.quotation_items_id_seq', 2, true);


--
-- Name: quotations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.quotations_id_seq', 3, true);


--
-- Name: reference_standard_certificate_uncertainties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.reference_standard_certificate_uncertainties_id_seq', 1, false);


--
-- Name: reference_standard_certificates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.reference_standard_certificates_id_seq', 1, false);


--
-- Name: reference_standard_uncertainties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.reference_standard_uncertainties_id_seq', 1, false);


--
-- Name: reference_standards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.reference_standards_id_seq', 1, false);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.roles_id_seq', 8, true);


--
-- Name: service_order_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.service_order_items_id_seq', 3, true);


--
-- Name: service_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.service_orders_id_seq', 4, true);


--
-- Name: technical_profile_allowed_patterns_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.technical_profile_allowed_patterns_id_seq', 1, false);


--
-- Name: technical_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.technical_profiles_id_seq', 1, true);


--
-- Name: uncertainty_calculations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_calculations_id_seq', 1, false);


--
-- Name: uncertainty_components_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_components_id_seq', 1, false);


--
-- Name: uncertainty_formulas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_formulas_id_seq', 1, false);


--
-- Name: uncertainty_model_exceptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_model_exceptions_id_seq', 1, false);


--
-- Name: uncertainty_model_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_model_versions_id_seq', 1, false);


--
-- Name: uncertainty_models_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_models_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.users_id_seq', 1, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: calibration_procedures calibration_procedures_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.calibration_procedures
    ADD CONSTRAINT calibration_procedures_pkey PRIMARY KEY (id);


--
-- Name: catalog_items catalog_items_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.catalog_items
    ADD CONSTRAINT catalog_items_pkey PRIMARY KEY (id);


--
-- Name: certificates certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_pkey PRIMARY KEY (id);


--
-- Name: client_contacts client_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.client_contacts
    ADD CONSTRAINT client_contacts_pkey PRIMARY KEY (id);


--
-- Name: clients clients_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_pkey PRIMARY KEY (id);


--
-- Name: controlled_document_versions controlled_document_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_pkey PRIMARY KEY (id);


--
-- Name: controlled_documents controlled_documents_code_key; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_documents
    ADD CONSTRAINT controlled_documents_code_key UNIQUE (code);


--
-- Name: controlled_documents controlled_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_documents
    ADD CONSTRAINT controlled_documents_pkey PRIMARY KEY (id);


--
-- Name: document_interpretations document_interpretations_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_pkey PRIMARY KEY (id);


--
-- Name: document_templates document_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_templates
    ADD CONSTRAINT document_templates_pkey PRIMARY KEY (id);


--
-- Name: document_templates document_templates_template_key_key; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_templates
    ADD CONSTRAINT document_templates_template_key_key UNIQUE (template_key);


--
-- Name: equipment equipment_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.equipment
    ADD CONSTRAINT equipment_pkey PRIMARY KEY (id);


--
-- Name: field_sheet_reference_standards field_sheet_reference_standards_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT field_sheet_reference_standards_pkey PRIMARY KEY (id);


--
-- Name: field_sheet_results field_sheet_results_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_results
    ADD CONSTRAINT field_sheet_results_pkey PRIMARY KEY (id);


--
-- Name: field_sheets field_sheets_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets
    ADD CONSTRAINT field_sheets_pkey PRIMARY KEY (id);


--
-- Name: quotation_items quotation_items_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_pkey PRIMARY KEY (id);


--
-- Name: quotations quotations_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_pkey PRIMARY KEY (id);


--
-- Name: reference_standard_certificate_uncertainties reference_standard_certificate_uncertainties_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificate_uncertainties
    ADD CONSTRAINT reference_standard_certificate_uncertainties_pkey PRIMARY KEY (id);


--
-- Name: reference_standard_certificates reference_standard_certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_pkey PRIMARY KEY (id);


--
-- Name: reference_standard_uncertainties reference_standard_uncertainties_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_uncertainties
    ADD CONSTRAINT reference_standard_uncertainties_pkey PRIMARY KEY (id);


--
-- Name: reference_standards reference_standards_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standards
    ADD CONSTRAINT reference_standards_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: service_order_items service_order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_order_items
    ADD CONSTRAINT service_order_items_pkey PRIMARY KEY (id);


--
-- Name: service_orders service_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT service_orders_pkey PRIMARY KEY (id);


--
-- Name: technical_profile_allowed_patterns technical_profile_allowed_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profile_allowed_patterns
    ADD CONSTRAINT technical_profile_allowed_patterns_pkey PRIMARY KEY (id);


--
-- Name: technical_profiles technical_profiles_code_key; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_code_key UNIQUE (code);


--
-- Name: technical_profiles technical_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_calculations uncertainty_calculations_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations
    ADD CONSTRAINT uncertainty_calculations_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_components uncertainty_components_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_components
    ADD CONSTRAINT uncertainty_components_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_formulas uncertainty_formulas_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_formulas
    ADD CONSTRAINT uncertainty_formulas_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_model_versions uncertainty_model_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uncertainty_model_versions_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_models uncertainty_models_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_models
    ADD CONSTRAINT uncertainty_models_pkey PRIMARY KEY (id);


--
-- Name: field_sheet_reference_standards uq_field_sheet_reference_standard_usage; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT uq_field_sheet_reference_standard_usage UNIQUE (field_sheet_id, reference_standard_id, usage_role, measurement_section);


--
-- Name: field_sheet_results uq_field_sheet_results_row; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_results
    ADD CONSTRAINT uq_field_sheet_results_row UNIQUE (field_sheet_id, section_key, row_number);


--
-- Name: uncertainty_model_versions uq_uncertainty_model_versions_number; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uq_uncertainty_model_versions_number UNIQUE (model_id, version_number);


--
-- Name: uncertainty_models uq_uncertainty_models_code_version; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_models
    ADD CONSTRAINT uq_uncertainty_models_code_version UNIQUE (code, version);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_entity; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_entity ON public.audit_logs USING btree (entity);


--
-- Name: ix_audit_logs_entity_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_entity_id ON public.audit_logs USING btree (entity_id);


--
-- Name: ix_audit_logs_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_id ON public.audit_logs USING btree (id);


--
-- Name: ix_audit_logs_user_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: ix_calibration_procedures_certificate_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_certificate_type ON public.calibration_procedures USING btree (certificate_type);


--
-- Name: ix_calibration_procedures_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_code ON public.calibration_procedures USING btree (code);


--
-- Name: ix_calibration_procedures_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_id ON public.calibration_procedures USING btree (id);


--
-- Name: ix_calibration_procedures_issuer_company; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_issuer_company ON public.calibration_procedures USING btree (issuer_company);


--
-- Name: ix_calibration_procedures_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_magnitude ON public.calibration_procedures USING btree (magnitude);


--
-- Name: ix_calibration_procedures_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_name ON public.calibration_procedures USING btree (name);


--
-- Name: ix_calibration_procedures_profile_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_profile_key ON public.calibration_procedures USING btree (profile_key);


--
-- Name: ix_calibration_procedures_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_status ON public.calibration_procedures USING btree (status);


--
-- Name: ix_calibration_procedures_uncertainty_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_uncertainty_model_id ON public.calibration_procedures USING btree (uncertainty_model_id);


--
-- Name: ix_calibration_procedures_uncertainty_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_uncertainty_model_version_id ON public.calibration_procedures USING btree (uncertainty_model_version_id);


--
-- Name: ix_calibration_procedures_version; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_version ON public.calibration_procedures USING btree (version);


--
-- Name: ix_catalog_items_category; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_category ON public.catalog_items USING btree (category);


--
-- Name: ix_catalog_items_commodity; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_commodity ON public.catalog_items USING btree (commodity);


--
-- Name: ix_catalog_items_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_id ON public.catalog_items USING btree (id);


--
-- Name: ix_catalog_items_internal_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_internal_key ON public.catalog_items USING btree (internal_key);


--
-- Name: ix_catalog_items_is_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_is_active ON public.catalog_items USING btree (is_active);


--
-- Name: ix_catalog_items_item_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_item_type ON public.catalog_items USING btree (item_type);


--
-- Name: ix_catalog_items_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_name ON public.catalog_items USING btree (name);


--
-- Name: ix_catalog_items_origin_currency; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_origin_currency ON public.catalog_items USING btree (origin_currency);


--
-- Name: ix_catalog_items_tax_object; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_tax_object ON public.catalog_items USING btree (tax_object);


--
-- Name: ix_certificates_authenticated_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_authenticated_by_id ON public.certificates USING btree (authenticated_by_id);


--
-- Name: ix_certificates_authentication_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_certificates_authentication_code ON public.certificates USING btree (authentication_code);


--
-- Name: ix_certificates_authentication_hash; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_authentication_hash ON public.certificates USING btree (authentication_hash);


--
-- Name: ix_certificates_capture_started_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_capture_started_by_id ON public.certificates USING btree (capture_started_by_id);


--
-- Name: ix_certificates_certificate_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_certificate_type ON public.certificates USING btree (certificate_type);


--
-- Name: ix_certificates_client_visible; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_client_visible ON public.certificates USING btree (client_visible);


--
-- Name: ix_certificates_equipment_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_equipment_id ON public.certificates USING btree (equipment_id);


--
-- Name: ix_certificates_expected_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_certificates_expected_folio ON public.certificates USING btree (expected_folio);


--
-- Name: ix_certificates_external_source; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_external_source ON public.certificates USING btree (external_source);


--
-- Name: ix_certificates_field_sheet_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_field_sheet_id ON public.certificates USING btree (field_sheet_id);


--
-- Name: ix_certificates_final_pdf_uploaded_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_final_pdf_uploaded_by_id ON public.certificates USING btree (final_pdf_uploaded_by_id);


--
-- Name: ix_certificates_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_certificates_folio ON public.certificates USING btree (folio);


--
-- Name: ix_certificates_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_id ON public.certificates USING btree (id);


--
-- Name: ix_certificates_match_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_match_status ON public.certificates USING btree (match_status);


--
-- Name: ix_certificates_quality_reviewed_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_quality_reviewed_by_id ON public.certificates USING btree (quality_reviewed_by_id);


--
-- Name: ix_certificates_released_to_client_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_released_to_client_by_id ON public.certificates USING btree (released_to_client_by_id);


--
-- Name: ix_certificates_sent_to_quality_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_sent_to_quality_by_id ON public.certificates USING btree (sent_to_quality_by_id);


--
-- Name: ix_certificates_service_order_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_service_order_id ON public.certificates USING btree (service_order_id);


--
-- Name: ix_certificates_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_status ON public.certificates USING btree (status);


--
-- Name: ix_client_contacts_client_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_client_contacts_client_id ON public.client_contacts USING btree (client_id);


--
-- Name: ix_client_contacts_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_client_contacts_id ON public.client_contacts USING btree (id);


--
-- Name: ix_clients_commercial_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_commercial_name ON public.clients USING btree (commercial_name);


--
-- Name: ix_clients_email; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_email ON public.clients USING btree (email);


--
-- Name: ix_clients_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_id ON public.clients USING btree (id);


--
-- Name: ix_clients_legal_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_legal_name ON public.clients USING btree (legal_name);


--
-- Name: ix_clients_rfc; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_rfc ON public.clients USING btree (rfc);


--
-- Name: ix_controlled_document_versions_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_approved_by_id ON public.controlled_document_versions USING btree (approved_by_id);


--
-- Name: ix_controlled_document_versions_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_document_id ON public.controlled_document_versions USING btree (document_id);


--
-- Name: ix_controlled_document_versions_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_id ON public.controlled_document_versions USING btree (id);


--
-- Name: ix_controlled_document_versions_reviewed_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_reviewed_by_id ON public.controlled_document_versions USING btree (reviewed_by_id);


--
-- Name: ix_controlled_document_versions_revision; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_revision ON public.controlled_document_versions USING btree (revision);


--
-- Name: ix_controlled_document_versions_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_status ON public.controlled_document_versions USING btree (status);


--
-- Name: ix_controlled_document_versions_uploaded_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_uploaded_by_id ON public.controlled_document_versions USING btree (uploaded_by_id);


--
-- Name: ix_controlled_documents_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_controlled_documents_code ON public.controlled_documents USING btree (code);


--
-- Name: ix_controlled_documents_created_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_created_by_id ON public.controlled_documents USING btree (created_by_id);


--
-- Name: ix_controlled_documents_document_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_document_type ON public.controlled_documents USING btree (document_type);


--
-- Name: ix_controlled_documents_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_id ON public.controlled_documents USING btree (id);


--
-- Name: ix_controlled_documents_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_name ON public.controlled_documents USING btree (name);


--
-- Name: ix_controlled_documents_quality_level; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_quality_level ON public.controlled_documents USING btree (quality_level);


--
-- Name: ix_controlled_documents_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_status ON public.controlled_documents USING btree (status);


--
-- Name: ix_document_interpretations_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_approved_by_id ON public.document_interpretations USING btree (approved_by_id);


--
-- Name: ix_document_interpretations_calibration_scope; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_calibration_scope ON public.document_interpretations USING btree (calibration_scope);


--
-- Name: ix_document_interpretations_created_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_created_by_id ON public.document_interpretations USING btree (created_by_id);


--
-- Name: ix_document_interpretations_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_document_id ON public.document_interpretations USING btree (document_id);


--
-- Name: ix_document_interpretations_document_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_document_version_id ON public.document_interpretations USING btree (document_version_id);


--
-- Name: ix_document_interpretations_equipment_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_equipment_type ON public.document_interpretations USING btree (equipment_type);


--
-- Name: ix_document_interpretations_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_id ON public.document_interpretations USING btree (id);


--
-- Name: ix_document_interpretations_interpretation_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_interpretation_type ON public.document_interpretations USING btree (interpretation_type);


--
-- Name: ix_document_interpretations_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_magnitude ON public.document_interpretations USING btree (magnitude);


--
-- Name: ix_document_interpretations_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_name ON public.document_interpretations USING btree (name);


--
-- Name: ix_document_interpretations_service_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_service_type ON public.document_interpretations USING btree (service_type);


--
-- Name: ix_document_interpretations_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_status ON public.document_interpretations USING btree (status);


--
-- Name: ix_document_templates_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_templates_id ON public.document_templates USING btree (id);


--
-- Name: ix_document_templates_template_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_document_templates_template_key ON public.document_templates USING btree (template_key);


--
-- Name: ix_equipment_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_id ON public.equipment USING btree (id);


--
-- Name: ix_equipment_internal_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_internal_id ON public.equipment USING btree (internal_id);


--
-- Name: ix_equipment_serial_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_serial_number ON public.equipment USING btree (serial_number);


--
-- Name: ix_equipment_service_order_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_service_order_id ON public.equipment USING btree (service_order_id);


--
-- Name: ix_equipment_service_order_item_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_service_order_item_id ON public.equipment USING btree (service_order_item_id);


--
-- Name: ix_equipment_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_status ON public.equipment USING btree (status);


--
-- Name: ix_field_sheet_reference_standards_field_sheet_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_field_sheet_id ON public.field_sheet_reference_standards USING btree (field_sheet_id);


--
-- Name: ix_field_sheet_reference_standards_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_id ON public.field_sheet_reference_standards USING btree (id);


--
-- Name: ix_field_sheet_reference_standards_reference_standard_c_5cb4; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_reference_standard_c_5cb4 ON public.field_sheet_reference_standards USING btree (reference_standard_certificate_id);


--
-- Name: ix_field_sheet_reference_standards_reference_standard_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_reference_standard_id ON public.field_sheet_reference_standards USING btree (reference_standard_id);


--
-- Name: ix_field_sheet_reference_standards_selected_uncertainty_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_selected_uncertainty_id ON public.field_sheet_reference_standards USING btree (selected_uncertainty_id);


--
-- Name: ix_field_sheet_results_field_sheet_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_results_field_sheet_id ON public.field_sheet_results USING btree (field_sheet_id);


--
-- Name: ix_field_sheet_results_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_results_id ON public.field_sheet_results USING btree (id);


--
-- Name: ix_field_sheet_results_section_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_results_section_key ON public.field_sheet_results USING btree (section_key);


--
-- Name: ix_field_sheets_calibration_procedure_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_calibration_procedure_id ON public.field_sheets USING btree (calibration_procedure_id);


--
-- Name: ix_field_sheets_equipment_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_equipment_id ON public.field_sheets USING btree (equipment_id);


--
-- Name: ix_field_sheets_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_id ON public.field_sheets USING btree (id);


--
-- Name: ix_field_sheets_returned_to_technician_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_returned_to_technician_by_id ON public.field_sheets USING btree (returned_to_technician_by_id);


--
-- Name: ix_field_sheets_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_status ON public.field_sheets USING btree (status);


--
-- Name: ix_field_sheets_template_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_template_key ON public.field_sheets USING btree (template_key);


--
-- Name: ix_field_sheets_work_order_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_work_order_number ON public.field_sheets USING btree (work_order_number);


--
-- Name: ix_quotation_items_catalog_item_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotation_items_catalog_item_id ON public.quotation_items USING btree (catalog_item_id);


--
-- Name: ix_quotation_items_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotation_items_id ON public.quotation_items USING btree (id);


--
-- Name: ix_quotation_items_quotation_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotation_items_quotation_id ON public.quotation_items USING btree (quotation_id);


--
-- Name: ix_quotations_advisor_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotations_advisor_id ON public.quotations USING btree (advisor_id);


--
-- Name: ix_quotations_client_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotations_client_id ON public.quotations USING btree (client_id);


--
-- Name: ix_quotations_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_quotations_folio ON public.quotations USING btree (folio);


--
-- Name: ix_quotations_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotations_id ON public.quotations USING btree (id);


--
-- Name: ix_quotations_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotations_status ON public.quotations USING btree (status);


--
-- Name: ix_reference_standard_certificate_uncertainties_certificate_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_certificate_id ON public.reference_standard_certificate_uncertainties USING btree (certificate_id);


--
-- Name: ix_reference_standard_certificate_uncertainties_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_id ON public.reference_standard_certificate_uncertainties USING btree (id);


--
-- Name: ix_reference_standard_certificate_uncertainties_is_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_is_active ON public.reference_standard_certificate_uncertainties USING btree (is_active);


--
-- Name: ix_reference_standard_certificate_uncertainties_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_magnitude ON public.reference_standard_certificate_uncertainties USING btree (magnitude);


--
-- Name: ix_reference_standard_certificate_uncertainties_measure_76de; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_measure_76de ON public.reference_standard_certificate_uncertainties USING btree (measurement_type);


--
-- Name: ix_reference_standard_certificate_uncertainties_range_max; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_range_max ON public.reference_standard_certificate_uncertainties USING btree (range_max);


--
-- Name: ix_reference_standard_certificate_uncertainties_range_min; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_range_min ON public.reference_standard_certificate_uncertainties USING btree (range_min);


--
-- Name: ix_reference_standard_certificate_uncertainties_unit; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_unit ON public.reference_standard_certificate_uncertainties USING btree (unit);


--
-- Name: ix_reference_standard_certificates_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_approved_by_id ON public.reference_standard_certificates USING btree (approved_by_id);


--
-- Name: ix_reference_standard_certificates_certificate_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_certificate_number ON public.reference_standard_certificates USING btree (certificate_number);


--
-- Name: ix_reference_standard_certificates_controlled_document__82a6; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_controlled_document__82a6 ON public.reference_standard_certificates USING btree (controlled_document_version_id);


--
-- Name: ix_reference_standard_certificates_controlled_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_controlled_document_id ON public.reference_standard_certificates USING btree (controlled_document_id);


--
-- Name: ix_reference_standard_certificates_created_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_created_by_id ON public.reference_standard_certificates USING btree (created_by_id);


--
-- Name: ix_reference_standard_certificates_expiration_date; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_expiration_date ON public.reference_standard_certificates USING btree (expiration_date);


--
-- Name: ix_reference_standard_certificates_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_id ON public.reference_standard_certificates USING btree (id);


--
-- Name: ix_reference_standard_certificates_is_current; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_is_current ON public.reference_standard_certificates USING btree (is_current);


--
-- Name: ix_reference_standard_certificates_reference_standard_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_reference_standard_id ON public.reference_standard_certificates USING btree (reference_standard_id);


--
-- Name: ix_reference_standard_certificates_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_status ON public.reference_standard_certificates USING btree (status);


--
-- Name: ix_reference_standard_uncertainties_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_uncertainties_id ON public.reference_standard_uncertainties USING btree (id);


--
-- Name: ix_reference_standard_uncertainties_reference_standard_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_uncertainties_reference_standard_id ON public.reference_standard_uncertainties USING btree (reference_standard_id);


--
-- Name: ix_reference_standards_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_id ON public.reference_standards USING btree (id);


--
-- Name: ix_reference_standards_internal_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_internal_code ON public.reference_standards USING btree (internal_code);


--
-- Name: ix_reference_standards_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_magnitude ON public.reference_standards USING btree (magnitude);


--
-- Name: ix_reference_standards_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_name ON public.reference_standards USING btree (name);


--
-- Name: ix_reference_standards_next_calibration_on; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_next_calibration_on ON public.reference_standards USING btree (next_calibration_on);


--
-- Name: ix_reference_standards_owner_company; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_owner_company ON public.reference_standards USING btree (owner_company);


--
-- Name: ix_reference_standards_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_status ON public.reference_standards USING btree (status);


--
-- Name: ix_roles_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_roles_id ON public.roles USING btree (id);


--
-- Name: ix_roles_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_roles_name ON public.roles USING btree (name);


--
-- Name: ix_service_order_items_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_order_items_id ON public.service_order_items USING btree (id);


--
-- Name: ix_service_order_items_service_order_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_order_items_service_order_id ON public.service_order_items USING btree (service_order_id);


--
-- Name: ix_service_orders_advisor_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_advisor_id ON public.service_orders USING btree (advisor_id);


--
-- Name: ix_service_orders_client_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_client_id ON public.service_orders USING btree (client_id);


--
-- Name: ix_service_orders_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_service_orders_folio ON public.service_orders USING btree (folio);


--
-- Name: ix_service_orders_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_id ON public.service_orders USING btree (id);


--
-- Name: ix_service_orders_quotation_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_quotation_id ON public.service_orders USING btree (quotation_id);


--
-- Name: ix_service_orders_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_status ON public.service_orders USING btree (status);


--
-- Name: ix_service_orders_technician_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_technician_id ON public.service_orders USING btree (technician_id);


--
-- Name: ix_service_orders_work_order_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_service_orders_work_order_number ON public.service_orders USING btree (work_order_number);


--
-- Name: ix_technical_profile_allowed_patterns_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profile_allowed_patterns_id ON public.technical_profile_allowed_patterns USING btree (id);


--
-- Name: ix_technical_profile_allowed_patterns_pattern_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profile_allowed_patterns_pattern_code ON public.technical_profile_allowed_patterns USING btree (pattern_code);


--
-- Name: ix_technical_profile_allowed_patterns_pattern_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profile_allowed_patterns_pattern_id ON public.technical_profile_allowed_patterns USING btree (pattern_id);


--
-- Name: ix_technical_profile_allowed_patterns_technical_profile_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profile_allowed_patterns_technical_profile_id ON public.technical_profile_allowed_patterns USING btree (technical_profile_id);


--
-- Name: ix_technical_profiles_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_approved_by_id ON public.technical_profiles USING btree (approved_by_id);


--
-- Name: ix_technical_profiles_calibration_scope; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_calibration_scope ON public.technical_profiles USING btree (calibration_scope);


--
-- Name: ix_technical_profiles_certificate_template_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_certificate_template_document_id ON public.technical_profiles USING btree (certificate_template_document_id);


--
-- Name: ix_technical_profiles_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_technical_profiles_code ON public.technical_profiles USING btree (code);


--
-- Name: ix_technical_profiles_created_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_created_by_id ON public.technical_profiles USING btree (created_by_id);


--
-- Name: ix_technical_profiles_equipment_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_equipment_type ON public.technical_profiles USING btree (equipment_type);


--
-- Name: ix_technical_profiles_field_sheet_template_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_field_sheet_template_document_id ON public.technical_profiles USING btree (field_sheet_template_document_id);


--
-- Name: ix_technical_profiles_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_id ON public.technical_profiles USING btree (id);


--
-- Name: ix_technical_profiles_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_magnitude ON public.technical_profiles USING btree (magnitude);


--
-- Name: ix_technical_profiles_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_name ON public.technical_profiles USING btree (name);


--
-- Name: ix_technical_profiles_procedure_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_procedure_document_id ON public.technical_profiles USING btree (procedure_document_id);


--
-- Name: ix_technical_profiles_procedure_interpretation_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_procedure_interpretation_id ON public.technical_profiles USING btree (procedure_interpretation_id);


--
-- Name: ix_technical_profiles_service_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_service_type ON public.technical_profiles USING btree (service_type);


--
-- Name: ix_technical_profiles_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_status ON public.technical_profiles USING btree (status);


--
-- Name: ix_technical_profiles_uncertainty_source_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_uncertainty_source_document_id ON public.technical_profiles USING btree (uncertainty_source_document_id);


--
-- Name: ix_uncertainty_calculations_field_sheet_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_calculations_field_sheet_id ON public.uncertainty_calculations USING btree (field_sheet_id);


--
-- Name: ix_uncertainty_calculations_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_calculations_status ON public.uncertainty_calculations USING btree (status);


--
-- Name: ix_uncertainty_calculations_uncertainty_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_calculations_uncertainty_model_id ON public.uncertainty_calculations USING btree (uncertainty_model_id);


--
-- Name: ix_uncertainty_calculations_uncertainty_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_calculations_uncertainty_model_version_id ON public.uncertainty_calculations USING btree (uncertainty_model_version_id);


--
-- Name: ix_uncertainty_components_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_components_key ON public.uncertainty_components USING btree (key);


--
-- Name: ix_uncertainty_components_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_components_model_id ON public.uncertainty_components USING btree (model_id);


--
-- Name: ix_uncertainty_components_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_components_model_version_id ON public.uncertainty_components USING btree (model_version_id);


--
-- Name: ix_uncertainty_components_source_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_components_source_type ON public.uncertainty_components USING btree (source_type);


--
-- Name: ix_uncertainty_formulas_is_active_formula; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_is_active_formula ON public.uncertainty_formulas USING btree (is_active_formula);


--
-- Name: ix_uncertainty_formulas_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_key ON public.uncertainty_formulas USING btree (key);


--
-- Name: ix_uncertainty_formulas_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_model_id ON public.uncertainty_formulas USING btree (model_id);


--
-- Name: ix_uncertainty_formulas_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_model_version_id ON public.uncertainty_formulas USING btree (model_version_id);


--
-- Name: ix_uncertainty_formulas_result_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_result_key ON public.uncertainty_formulas USING btree (result_key);


--
-- Name: ix_uncertainty_model_exceptions_alternate_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_alternate_model_id ON public.uncertainty_model_exceptions USING btree (alternate_model_id);


--
-- Name: ix_uncertainty_model_exceptions_alternate_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_alternate_model_version_id ON public.uncertainty_model_exceptions USING btree (alternate_model_version_id);


--
-- Name: ix_uncertainty_model_exceptions_base_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_base_model_id ON public.uncertainty_model_exceptions USING btree (base_model_id);


--
-- Name: ix_uncertainty_model_exceptions_base_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_base_model_version_id ON public.uncertainty_model_exceptions USING btree (base_model_version_id);


--
-- Name: ix_uncertainty_model_exceptions_equipment_model; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_equipment_model ON public.uncertainty_model_exceptions USING btree (equipment_model);


--
-- Name: ix_uncertainty_model_exceptions_equipment_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_equipment_type ON public.uncertainty_model_exceptions USING btree (equipment_type);


--
-- Name: ix_uncertainty_model_exceptions_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_magnitude ON public.uncertainty_model_exceptions USING btree (magnitude);


--
-- Name: ix_uncertainty_model_exceptions_procedure_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_procedure_id ON public.uncertainty_model_exceptions USING btree (procedure_id);


--
-- Name: ix_uncertainty_model_exceptions_profile_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_profile_key ON public.uncertainty_model_exceptions USING btree (profile_key);


--
-- Name: ix_uncertainty_model_exceptions_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_status ON public.uncertainty_model_exceptions USING btree (status);


--
-- Name: ix_uncertainty_model_versions_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_approved_by_id ON public.uncertainty_model_versions USING btree (approved_by_id);


--
-- Name: ix_uncertainty_model_versions_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_model_id ON public.uncertainty_model_versions USING btree (model_id);


--
-- Name: ix_uncertainty_model_versions_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_status ON public.uncertainty_model_versions USING btree (status);


--
-- Name: ix_uncertainty_model_versions_submitted_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_submitted_by_id ON public.uncertainty_model_versions USING btree (submitted_by_id);


--
-- Name: ix_uncertainty_model_versions_version_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_version_number ON public.uncertainty_model_versions USING btree (version_number);


--
-- Name: ix_uncertainty_models_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_code ON public.uncertainty_models USING btree (code);


--
-- Name: ix_uncertainty_models_equipment_family; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_equipment_family ON public.uncertainty_models USING btree (equipment_family);


--
-- Name: ix_uncertainty_models_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_magnitude ON public.uncertainty_models USING btree (magnitude);


--
-- Name: ix_uncertainty_models_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_name ON public.uncertainty_models USING btree (name);


--
-- Name: ix_uncertainty_models_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_status ON public.uncertainty_models USING btree (status);


--
-- Name: ix_uncertainty_models_version; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_version ON public.uncertainty_models USING btree (version);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: uq_calibration_procedures_code_version_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_calibration_procedures_code_version_active ON public.calibration_procedures USING btree (code, version) WHERE (is_active = true);


--
-- Name: uq_catalog_items_internal_key_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_catalog_items_internal_key_active ON public.catalog_items USING btree (internal_key) WHERE ((is_active = true) AND (internal_key IS NOT NULL));


--
-- Name: uq_certificates_active_field_sheet; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_certificates_active_field_sheet ON public.certificates USING btree (field_sheet_id) WHERE (is_active IS TRUE);


--
-- Name: uq_controlled_document_one_active_version; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_controlled_document_one_active_version ON public.controlled_document_versions USING btree (document_id) WHERE ((status)::text = 'active'::text);


--
-- Name: uq_field_sheets_active_equipment; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_field_sheets_active_equipment ON public.field_sheets USING btree (equipment_id) WHERE (is_active IS TRUE);


--
-- Name: uq_reference_standard_current_certificate; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_reference_standard_current_certificate ON public.reference_standard_certificates USING btree (reference_standard_id) WHERE (is_current = true);


--
-- Name: uq_reference_standards_internal_code_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_reference_standards_internal_code_active ON public.reference_standards USING btree (internal_code) WHERE (is_active = true);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: certificates certificates_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id);


--
-- Name: certificates certificates_field_sheet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_field_sheet_id_fkey FOREIGN KEY (field_sheet_id) REFERENCES public.field_sheets(id);


--
-- Name: certificates certificates_service_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_service_order_id_fkey FOREIGN KEY (service_order_id) REFERENCES public.service_orders(id);


--
-- Name: client_contacts client_contacts_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.client_contacts
    ADD CONSTRAINT client_contacts_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: controlled_document_versions controlled_document_versions_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: controlled_document_versions controlled_document_versions_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.controlled_documents(id);


--
-- Name: controlled_document_versions controlled_document_versions_reviewed_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_reviewed_by_id_fkey FOREIGN KEY (reviewed_by_id) REFERENCES public.users(id);


--
-- Name: controlled_document_versions controlled_document_versions_uploaded_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_uploaded_by_id_fkey FOREIGN KEY (uploaded_by_id) REFERENCES public.users(id);


--
-- Name: controlled_documents controlled_documents_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_documents
    ADD CONSTRAINT controlled_documents_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: document_interpretations document_interpretations_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: document_interpretations document_interpretations_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: document_interpretations document_interpretations_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.controlled_documents(id);


--
-- Name: document_interpretations document_interpretations_document_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_document_version_id_fkey FOREIGN KEY (document_version_id) REFERENCES public.controlled_document_versions(id);


--
-- Name: equipment equipment_service_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.equipment
    ADD CONSTRAINT equipment_service_order_id_fkey FOREIGN KEY (service_order_id) REFERENCES public.service_orders(id);


--
-- Name: equipment equipment_service_order_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.equipment
    ADD CONSTRAINT equipment_service_order_item_id_fkey FOREIGN KEY (service_order_item_id) REFERENCES public.service_order_items(id);


--
-- Name: field_sheet_reference_standards field_sheet_reference_standards_field_sheet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT field_sheet_reference_standards_field_sheet_id_fkey FOREIGN KEY (field_sheet_id) REFERENCES public.field_sheets(id);


--
-- Name: field_sheet_reference_standards field_sheet_reference_standards_reference_standard_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT field_sheet_reference_standards_reference_standard_id_fkey FOREIGN KEY (reference_standard_id) REFERENCES public.reference_standards(id);


--
-- Name: field_sheet_results field_sheet_results_field_sheet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_results
    ADD CONSTRAINT field_sheet_results_field_sheet_id_fkey FOREIGN KEY (field_sheet_id) REFERENCES public.field_sheets(id);


--
-- Name: field_sheets field_sheets_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets
    ADD CONSTRAINT field_sheets_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id);


--
-- Name: calibration_procedures fk_calibration_procedures_uncertainty_model_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.calibration_procedures
    ADD CONSTRAINT fk_calibration_procedures_uncertainty_model_id FOREIGN KEY (uncertainty_model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: calibration_procedures fk_calibration_procedures_uncertainty_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.calibration_procedures
    ADD CONSTRAINT fk_calibration_procedures_uncertainty_model_version_id FOREIGN KEY (uncertainty_model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: certificates fk_certificates_authenticated_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_authenticated_by_id_users FOREIGN KEY (authenticated_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_capture_started_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_capture_started_by_id FOREIGN KEY (capture_started_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_final_pdf_uploaded_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_final_pdf_uploaded_by_id FOREIGN KEY (final_pdf_uploaded_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_quality_reviewed_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_quality_reviewed_by_id FOREIGN KEY (quality_reviewed_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_released_to_client_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_released_to_client_by_id FOREIGN KEY (released_to_client_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_sent_to_quality_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_sent_to_quality_by_id FOREIGN KEY (sent_to_quality_by_id) REFERENCES public.users(id);


--
-- Name: field_sheet_reference_standards fk_field_sheet_reference_standards_certificate_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT fk_field_sheet_reference_standards_certificate_id FOREIGN KEY (reference_standard_certificate_id) REFERENCES public.reference_standard_certificates(id);


--
-- Name: field_sheet_reference_standards fk_field_sheet_reference_standards_uncertainty_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT fk_field_sheet_reference_standards_uncertainty_id FOREIGN KEY (selected_uncertainty_id) REFERENCES public.reference_standard_certificate_uncertainties(id);


--
-- Name: field_sheets fk_field_sheets_calibration_procedure_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets
    ADD CONSTRAINT fk_field_sheets_calibration_procedure_id FOREIGN KEY (calibration_procedure_id) REFERENCES public.calibration_procedures(id);


--
-- Name: field_sheets fk_field_sheets_returned_to_technician_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets
    ADD CONSTRAINT fk_field_sheets_returned_to_technician_by_id_users FOREIGN KEY (returned_to_technician_by_id) REFERENCES public.users(id);


--
-- Name: quotation_items fk_quotation_items_catalog_item_id_catalog_items; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT fk_quotation_items_catalog_item_id_catalog_items FOREIGN KEY (catalog_item_id) REFERENCES public.catalog_items(id);


--
-- Name: service_orders fk_service_orders_advisor_id_users; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT fk_service_orders_advisor_id_users FOREIGN KEY (advisor_id) REFERENCES public.users(id);


--
-- Name: service_orders fk_service_orders_technician_id_users; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT fk_service_orders_technician_id_users FOREIGN KEY (technician_id) REFERENCES public.users(id);


--
-- Name: uncertainty_calculations fk_uncertainty_calculations_uncertainty_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations
    ADD CONSTRAINT fk_uncertainty_calculations_uncertainty_model_version_id FOREIGN KEY (uncertainty_model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: uncertainty_components fk_uncertainty_components_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_components
    ADD CONSTRAINT fk_uncertainty_components_model_version_id FOREIGN KEY (model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: uncertainty_formulas fk_uncertainty_formulas_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_formulas
    ADD CONSTRAINT fk_uncertainty_formulas_model_version_id FOREIGN KEY (model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: uncertainty_model_exceptions fk_uncertainty_model_exceptions_alternate_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT fk_uncertainty_model_exceptions_alternate_model_version_id FOREIGN KEY (alternate_model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: uncertainty_model_exceptions fk_uncertainty_model_exceptions_base_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT fk_uncertainty_model_exceptions_base_model_version_id FOREIGN KEY (base_model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: quotation_items quotation_items_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.quotations(id);


--
-- Name: quotations quotations_advisor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_advisor_id_fkey FOREIGN KEY (advisor_id) REFERENCES public.users(id);


--
-- Name: quotations quotations_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: reference_standard_certificates reference_standard_certificat_controlled_document_version__fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificat_controlled_document_version__fkey FOREIGN KEY (controlled_document_version_id) REFERENCES public.controlled_document_versions(id);


--
-- Name: reference_standard_certificate_uncertainties reference_standard_certificate_uncertaintie_certificate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificate_uncertainties
    ADD CONSTRAINT reference_standard_certificate_uncertaintie_certificate_id_fkey FOREIGN KEY (certificate_id) REFERENCES public.reference_standard_certificates(id);


--
-- Name: reference_standard_certificates reference_standard_certificates_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: reference_standard_certificates reference_standard_certificates_controlled_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_controlled_document_id_fkey FOREIGN KEY (controlled_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: reference_standard_certificates reference_standard_certificates_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: reference_standard_certificates reference_standard_certificates_reference_standard_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_reference_standard_id_fkey FOREIGN KEY (reference_standard_id) REFERENCES public.reference_standards(id);


--
-- Name: reference_standard_uncertainties reference_standard_uncertainties_reference_standard_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_uncertainties
    ADD CONSTRAINT reference_standard_uncertainties_reference_standard_id_fkey FOREIGN KEY (reference_standard_id) REFERENCES public.reference_standards(id);


--
-- Name: service_order_items service_order_items_quotation_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_order_items
    ADD CONSTRAINT service_order_items_quotation_item_id_fkey FOREIGN KEY (quotation_item_id) REFERENCES public.quotation_items(id);


--
-- Name: service_order_items service_order_items_service_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_order_items
    ADD CONSTRAINT service_order_items_service_order_id_fkey FOREIGN KEY (service_order_id) REFERENCES public.service_orders(id);


--
-- Name: service_orders service_orders_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT service_orders_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: service_orders service_orders_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT service_orders_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.quotations(id);


--
-- Name: technical_profile_allowed_patterns technical_profile_allowed_patterns_pattern_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profile_allowed_patterns
    ADD CONSTRAINT technical_profile_allowed_patterns_pattern_id_fkey FOREIGN KEY (pattern_id) REFERENCES public.reference_standards(id);


--
-- Name: technical_profile_allowed_patterns technical_profile_allowed_patterns_technical_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profile_allowed_patterns
    ADD CONSTRAINT technical_profile_allowed_patterns_technical_profile_id_fkey FOREIGN KEY (technical_profile_id) REFERENCES public.technical_profiles(id);


--
-- Name: technical_profiles technical_profiles_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: technical_profiles technical_profiles_certificate_template_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_certificate_template_document_id_fkey FOREIGN KEY (certificate_template_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: technical_profiles technical_profiles_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: technical_profiles technical_profiles_field_sheet_template_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_field_sheet_template_document_id_fkey FOREIGN KEY (field_sheet_template_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: technical_profiles technical_profiles_procedure_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_procedure_document_id_fkey FOREIGN KEY (procedure_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: technical_profiles technical_profiles_procedure_interpretation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_procedure_interpretation_id_fkey FOREIGN KEY (procedure_interpretation_id) REFERENCES public.document_interpretations(id);


--
-- Name: technical_profiles technical_profiles_uncertainty_source_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_uncertainty_source_document_id_fkey FOREIGN KEY (uncertainty_source_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: uncertainty_calculations uncertainty_calculations_field_sheet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations
    ADD CONSTRAINT uncertainty_calculations_field_sheet_id_fkey FOREIGN KEY (field_sheet_id) REFERENCES public.field_sheets(id);


--
-- Name: uncertainty_calculations uncertainty_calculations_uncertainty_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations
    ADD CONSTRAINT uncertainty_calculations_uncertainty_model_id_fkey FOREIGN KEY (uncertainty_model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_components uncertainty_components_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_components
    ADD CONSTRAINT uncertainty_components_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_formulas uncertainty_formulas_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_formulas
    ADD CONSTRAINT uncertainty_formulas_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_alternate_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_alternate_model_id_fkey FOREIGN KEY (alternate_model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_authorized_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_authorized_by_id_fkey FOREIGN KEY (authorized_by_id) REFERENCES public.users(id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_base_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_base_model_id_fkey FOREIGN KEY (base_model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_procedure_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_procedure_id_fkey FOREIGN KEY (procedure_id) REFERENCES public.calibration_procedures(id);


--
-- Name: uncertainty_model_versions uncertainty_model_versions_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uncertainty_model_versions_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: uncertainty_model_versions uncertainty_model_versions_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uncertainty_model_versions_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_model_versions uncertainty_model_versions_submitted_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uncertainty_model_versions_submitted_by_id_fkey FOREIGN KEY (submitted_by_id) REFERENCES public.users(id);


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: saulcortes
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict 2vJXHYbPV2YibMBPOtjBWHlwpDBU3SXXe8y3yzS8gXlHA5yeaFbDWirtnDs2gV0

