--
-- PostgreSQL database dump
--

\restrict L777Ft5y1CFUHNBar3KAMQtWjAEI0bNxzzNBPDuyAMckAX87U6R39VQCxtvV5DF

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
    deleted_by integer,
    cfdi_use character varying(40),
    street character varying(255),
    exterior_number character varying(40),
    interior_number character varying(40),
    neighborhood character varying(180),
    city character varying(180),
    state character varying(180),
    postal_code character varying(20),
    country character varying(120),
    fiscal_postal_code character varying(20),
    tax_constancy_filename character varying(255),
    tax_constancy_path character varying(500),
    tax_constancy_uploaded_at timestamp with time zone,
    client_type character varying(30) DEFAULT 'persona_moral'::character varying NOT NULL,
    curp character varying(18),
    first_name character varying(120),
    first_last_name character varying(120),
    second_last_name character varying(120),
    street_type character varying(80),
    locality character varying(180),
    municipality character varying(180)
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
-- Name: credit_notes; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.credit_notes (
    invoice_id integer NOT NULL,
    folio character varying(40) NOT NULL,
    issued_on date,
    reason text NOT NULL,
    subtotal numeric(12,2) NOT NULL,
    tax_total numeric(12,2) NOT NULL,
    total numeric(12,2) NOT NULL,
    status character varying(40) NOT NULL,
    observations text,
    created_by_id integer,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.credit_notes OWNER TO saulcortes;

--
-- Name: credit_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.credit_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.credit_notes_id_seq OWNER TO saulcortes;

--
-- Name: credit_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.credit_notes_id_seq OWNED BY public.credit_notes.id;


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
    deleted_by integer,
    calibration_scope character varying(60)
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
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_data json
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
-- Name: field_sheet_template_definitions; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.field_sheet_template_definitions (
    template_key character varying(60) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    status character varying(40) NOT NULL,
    version integer NOT NULL,
    definition_json json NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.field_sheet_template_definitions OWNER TO saulcortes;

--
-- Name: field_sheet_template_definitions_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.field_sheet_template_definitions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.field_sheet_template_definitions_id_seq OWNER TO saulcortes;

--
-- Name: field_sheet_template_definitions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.field_sheet_template_definitions_id_seq OWNED BY public.field_sheet_template_definitions.id;


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
    returned_to_technician_reason text,
    certificate_client_mode character varying(30) NOT NULL,
    certificate_client_company character varying(180),
    certificate_client_attention character varying(180),
    certificate_client_address text,
    apply_certificate_client_to_order boolean NOT NULL,
    minimum_division character varying(120),
    location character varying(180),
    attention character varying(180),
    company character varying(180),
    address text,
    template_definition_json json,
    template_definition_version integer
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
-- Name: invoice_items; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.invoice_items (
    invoice_id integer NOT NULL,
    quotation_item_id integer,
    certificate_id integer,
    equipment_id integer,
    description text NOT NULL,
    quantity numeric(12,2) NOT NULL,
    unit character varying(80),
    sat_unit character varying(40),
    sat_key character varying(40),
    unit_price numeric(12,2) NOT NULL,
    discount_total numeric(12,2) NOT NULL,
    tax_rate numeric(5,2) NOT NULL,
    tax_total numeric(12,2) NOT NULL,
    line_total numeric(12,2) NOT NULL,
    notes text,
    service_type character varying(80),
    source_type character varying(40),
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invoice_items OWNER TO saulcortes;

--
-- Name: invoice_items_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.invoice_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoice_items_id_seq OWNER TO saulcortes;

--
-- Name: invoice_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.invoice_items_id_seq OWNED BY public.invoice_items.id;


--
-- Name: invoice_payments; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.invoice_payments (
    invoice_id integer NOT NULL,
    paid_on date,
    amount numeric(12,2) NOT NULL,
    bank_name character varying(120),
    bank_account character varying(120),
    reference character varying(120),
    payment_method character varying(80),
    payment_form character varying(80),
    status character varying(40) NOT NULL,
    notes text,
    registered_by_id integer,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invoice_payments OWNER TO saulcortes;

--
-- Name: invoice_payments_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.invoice_payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoice_payments_id_seq OWNER TO saulcortes;

--
-- Name: invoice_payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.invoice_payments_id_seq OWNED BY public.invoice_payments.id;


--
-- Name: invoice_settings; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.invoice_settings (
    key character varying(60) NOT NULL,
    default_series character varying(20) NOT NULL,
    next_sequence integer NOT NULL,
    reset_annually boolean NOT NULL,
    default_tax_rate numeric(5,2) NOT NULL,
    default_currency character varying(10) NOT NULL,
    default_credit_days integer NOT NULL,
    allow_manual_folio boolean NOT NULL,
    forms_of_payment json,
    methods_of_payment json,
    usage_cfdi_catalog json,
    tax_regime_catalog json,
    currency_catalog json,
    sat_product_keys json,
    sat_units json,
    banks json,
    bank_accounts json,
    legal_texts json,
    billing_emails json,
    emitter_data json,
    pdf_template_name character varying(120),
    cfdi_future_parameters json,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invoice_settings OWNER TO saulcortes;

--
-- Name: invoice_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.invoice_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoice_settings_id_seq OWNER TO saulcortes;

--
-- Name: invoice_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.invoice_settings_id_seq OWNED BY public.invoice_settings.id;


--
-- Name: invoices; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.invoices (
    internal_uuid character varying(64) NOT NULL,
    series character varying(20) NOT NULL,
    folio character varying(40) NOT NULL,
    client_id integer NOT NULL,
    fiscal_client_id integer,
    service_order_id integer,
    quotation_id integer,
    issued_on date,
    due_on date,
    subtotal numeric(12,2) NOT NULL,
    tax_total numeric(12,2) NOT NULL,
    withholding_total numeric(12,2) NOT NULL,
    discount_total numeric(12,2) NOT NULL,
    total numeric(12,2) NOT NULL,
    balance_due numeric(12,2) NOT NULL,
    amount_paid numeric(12,2) NOT NULL,
    status character varying(40) NOT NULL,
    payment_method character varying(80),
    payment_form character varying(80),
    usage_cfdi character varying(80),
    currency character varying(10) NOT NULL,
    credit_days integer NOT NULL,
    observations text,
    internal_comments text,
    cancellation_reason text,
    created_by_id integer,
    updated_by_id integer,
    last_payment_on date,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invoices OWNER TO saulcortes;

--
-- Name: invoices_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.invoices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoices_id_seq OWNER TO saulcortes;

--
-- Name: invoices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.invoices_id_seq OWNED BY public.invoices.id;


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
    deleted_by integer,
    calibration_scope character varying(60)
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
-- Name: credit_notes id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.credit_notes ALTER COLUMN id SET DEFAULT nextval('public.credit_notes_id_seq'::regclass);


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
-- Name: field_sheet_template_definitions id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_template_definitions ALTER COLUMN id SET DEFAULT nextval('public.field_sheet_template_definitions_id_seq'::regclass);


--
-- Name: field_sheets id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets ALTER COLUMN id SET DEFAULT nextval('public.field_sheets_id_seq'::regclass);


--
-- Name: invoice_items id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items ALTER COLUMN id SET DEFAULT nextval('public.invoice_items_id_seq'::regclass);


--
-- Name: invoice_payments id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_payments ALTER COLUMN id SET DEFAULT nextval('public.invoice_payments_id_seq'::regclass);


--
-- Name: invoice_settings id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_settings ALTER COLUMN id SET DEFAULT nextval('public.invoice_settings_id_seq'::regclass);


--
-- Name: invoices id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices ALTER COLUMN id SET DEFAULT nextval('public.invoices_id_seq'::regclass);


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
2b3c4d5e6f7a
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.audit_logs (user_id, action, entity, entity_id, previous_values, new_values, comment, id, created_at, updated_at) FROM stdin;
\N	user.created	users	1	null	{"email": "saul@myc.com", "full_name": "admin", "is_active": true, "role_names": ["Administrador"]}	Registro inicial o alta desde auth.register	1	2026-07-06 12:48:46.001288-06	2026-07-06 12:48:46.001288-06
\N	client.created	clients	1	null	{"legal_name": "SAUL ISAAC ARCE CORTES", "rfc": "AECS020326TK6"}	\N	2	2026-07-06 13:12:59.095363-06	2026-07-06 13:12:59.095363-06
\N	catalog_item.created	catalog_items	1	null	{"name": "Servicio de calibraci\\u00f3n a man\\u00f3metro con rango de 0 - 500 psi", "internal_key": "SER-CAL-0001"}	\N	3	2026-07-06 16:22:56.407874-06	2026-07-06 16:22:56.407874-06
\N	quotation.created	quotations	1	null	{"folio": "MYC-07-26-0001", "client_id": 1, "total": "0.00"}	\N	4	2026-07-06 16:24:47.201901-06	2026-07-06 16:24:47.201901-06
\N	quotation.sent	quotations	1	{"status": "draft"}	{"status": "sent"}	\N	5	2026-07-06 16:29:53.97317-06	2026-07-06 16:29:53.97317-06
\N	quotation.accepted	quotations	1	{"status": "sent"}	{"status": "accepted"}	\N	6	2026-07-06 16:30:00.578162-06	2026-07-06 16:30:00.578162-06
\N	service_order.created	service_orders	1	null	{"folio": "OSMYC-26-07-0001", "work_order_number": 7001, "client_id": 1, "quotation_id": 1, "status": "scheduled"}	\N	7	2026-07-06 16:30:03.199625-06	2026-07-06 16:30:03.199625-06
\N	quotation.deactivated	quotations	1	{"is_active": true}	{"is_active": false}	\N	8	2026-07-06 16:31:10.703092-06	2026-07-06 16:31:10.703092-06
\N	service_order.deactivated	service_orders	1	{"is_active": true}	{"is_active": false}	\N	9	2026-07-06 16:31:14.788937-06	2026-07-06 16:31:14.788937-06
\N	quotation.created	quotations	2	null	{"folio": "MYC-07-26-0002", "client_id": 1, "total": "0.00"}	\N	10	2026-07-06 16:31:30.354774-06	2026-07-06 16:31:30.354774-06
\N	quotation.item_added	quotations	2	null	{"service_name": "Servicio de calibraci\\u00f3n a man\\u00f3metro con rango de 0 - 500 psi", "quantity": 1, "total": "2100.00"}	\N	11	2026-07-06 16:31:37.406952-06	2026-07-06 16:31:37.406952-06
\N	quotation.sent	quotations	2	{"status": "draft"}	{"status": "sent"}	\N	12	2026-07-06 16:33:40.267525-06	2026-07-06 16:33:40.267525-06
\N	quotation.accepted	quotations	2	{"status": "sent"}	{"status": "accepted"}	\N	13	2026-07-06 16:33:42.439395-06	2026-07-06 16:33:42.439395-06
\N	service_order.created	service_orders	2	null	{"folio": "OSMYC-26-07-0002", "work_order_number": 7002, "client_id": 1, "quotation_id": 2, "status": "scheduled"}	\N	14	2026-07-06 16:33:44.766109-06	2026-07-06 16:33:44.766109-06
\N	service_order.updated	service_orders	2	{"technician_id": null, "agenda_date": null, "service_date": null, "requires_payment": true, "notes": "Generada desde cotizacion MYC-07-26-0002"}	{"technician_id": null, "agenda_date": "2026-07-06", "service_date": "2026-07-07", "requires_payment": true, "notes": "Generada desde cotizacion MYC-07-26-0002"}	\N	15	2026-07-06 16:35:03.696469-06	2026-07-06 16:35:03.696469-06
\N	service_order.confirmed	service_orders	2	{"status": "scheduled"}	{"status": "confirmed"}	\N	16	2026-07-06 16:35:06.199699-06	2026-07-06 16:35:06.199699-06
\N	service_order.called	service_orders	2	{"status": "confirmed"}	{"status": "called"}	\N	17	2026-07-06 16:35:08.474888-06	2026-07-06 16:35:08.474888-06
\N	certificate.expected_created	certificates	1	null	{"folio": "MYCA-07-2026-0001", "expected_folio": "MYCA-07-2026-0001", "service_order_id": 2, "equipment_id": 1, "field_sheet_id": null, "status": "expected"}	\N	18	2026-07-06 16:36:29.866794-06	2026-07-06 16:36:29.866794-06
\N	equipment.created	equipment	1	null	{"service_order_id": 2, "calibration_scope": "accredited_iso_17025", "service_order_item_id": 1, "name": "Manometro", "status": "registered"}	\N	19	2026-07-06 16:36:29.912708-06	2026-07-06 16:36:29.912708-06
\N	equipment.realizing	equipment	1	{"status": "registered"}	{"status": "realizing"}	\N	20	2026-07-06 16:44:56.871259-06	2026-07-06 16:44:56.871259-06
\N	field_sheet.created	field_sheets	1	null	{"equipment_id": 1, "calibration_procedure_id": null, "template_key": "micrometro", "work_order_number": 7002, "status": "draft", "calibration_place": null, "minimum_division": null, "location": null, "attention": null, "company": null, "address": null, "reception_date": "2026-07-06", "calibration_date": "2026-07-07", "next_calibration_date": null, "environment_humidity_start": null, "environment_humidity_end": null, "environment_temperature_start": null, "environment_temperature_end": null, "equipment_general_condition": null, "consider_equipment_deviations": false, "units": null, "calibrated_by": null, "reviewed_by": null, "report_made_by": null, "purchase_order_or_quotation": "MYC-07-26-0002", "initial_condition": null, "final_condition": null, "pattern_used": null, "results": null, "observations": null, "evidence_notes": null, "method": null, "environmental_conditions": null, "technician_notes": null, "template_definition": {"id": 14, "source": "database", "template_key": "micrometro", "key": "micrometro", "name": "Hoja de Campo Micr\\u00f3metro", "description": null, "type": "micrometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}, "template_definition_version": 1, "certificate_client_mode": "billing", "certificate_client_company": null, "certificate_client_attention": null, "certificate_client_address": null, "apply_certificate_client_to_order": true, "reserved_certificate_folio": "MYCA-07-2026-0001", "results_rows": [{"id": 1, "section_key": "dimensional_4", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 2, "section_key": "dimensional_4", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 3, "section_key": "dimensional_4", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 4, "section_key": "dimensional_4", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 5, "section_key": "dimensional_4", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 6, "section_key": "dimensional_4", "row_number": 6, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 7, "section_key": "dimensional_4", "row_number": 7, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 8, "section_key": "dimensional_4", "row_number": 8, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 9, "section_key": "dimensional_4", "row_number": 9, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 10, "section_key": "dimensional_4", "row_number": 10, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 11, "section_key": "repeatability_5", "row_number": 1, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 12, "section_key": "repeatability_5", "row_number": 2, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 13, "section_key": "repeatability_5", "row_number": 3, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 14, "section_key": "repeatability_5", "row_number": 4, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}, {"id": 15, "section_key": "repeatability_5", "row_number": 5, "pattern_value": null, "ibc_value_1": null, "ibc_value_2": null, "ibc_value_3": null, "unit": null, "notes": null, "row_data": {}}], "reference_standards": []}	\N	21	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06
\N	client.created	clients	2	null	{"legal_name": "Cliente Prueba QA SA de CV", "rfc": "CPQ010101AB1", "commercial_name": "Cliente Prueba QA"}	\N	22	2026-07-06 17:10:14.284347-06	2026-07-06 17:10:14.284347-06
\N	client.tax_constancy_uploaded	clients	1	{"tax_constancy_filename": null, "tax_constancy_path": null}	{"tax_constancy_filename": "constancia_demo.pdf", "tax_constancy_path": "clientes/cliente_1/constancia_fiscal_ea80d3728e6e4992b55b41d441c4dc57.pdf"}	\N	23	2026-07-06 17:10:14.307728-06	2026-07-06 17:10:14.307728-06
\N	client.deactivated	clients	2	{"is_active": true}	{"is_active": false}	\N	24	2026-07-06 17:13:39.75213-06	2026-07-06 17:13:39.75213-06
\N	client.updated	clients	1	{"legal_name": "SAUL ISAAC ARCE CORTES", "commercial_name": "SAUL ISAAC ARCE CORTES", "rfc": "AECS020326TK6", "email": "saul.cortesoc@gmail.com", "phone": "3344827214", "tax_regime": "SIMPLIFICADO DE CONFIANZA", "cfdi_use": null, "street": null, "exterior_number": null, "interior_number": null, "neighborhood": null, "city": null, "state": null, "postal_code": null, "country": null, "fiscal_postal_code": null, "contacts": [{"name": "SAUL CORTES", "email": "saul.cortesoc@gmail.com", "phone": "3344827214"}]}	{"legal_name": "SAUL ISAAC ARCE CORTES", "commercial_name": "SAUL ISAAC ARCE CORTES", "rfc": "AECS020326TK6", "email": "saul.cortesoc@gmail.com", "phone": "3344827214", "tax_regime": "SIMPLIFICADO DE CONFIANZA", "cfdi_use": null, "street": null, "exterior_number": null, "interior_number": null, "neighborhood": null, "city": null, "state": null, "postal_code": null, "country": "Mexico", "fiscal_postal_code": null, "contacts": [{"name": "SAUL CORTES", "email": "saul.cortesoc@gmail.com", "phone": "3344827214", "position": null}]}	\N	25	2026-07-06 17:13:56.586214-06	2026-07-06 17:13:56.586214-06
\N	client.tax_constancy_uploaded	clients	1	{"tax_constancy_filename": "constancia_demo.pdf", "tax_constancy_path": "clientes/cliente_1/constancia_fiscal_ea80d3728e6e4992b55b41d441c4dc57.pdf"}	{"tax_constancy_filename": "Csf_MSM180712686.pdf", "tax_constancy_path": "clientes/cliente_1/constancia_fiscal_4c6b5f091cf64d8aa0e45dcf20c2868d.pdf"}	\N	26	2026-07-06 17:13:56.62414-06	2026-07-06 17:13:56.62414-06
\N	client.updated	clients	1	{"legal_name": "SAUL ISAAC ARCE CORTES", "commercial_name": "SAUL ISAAC ARCE CORTES", "rfc": "AECS020326TK6", "email": "saul.cortesoc@gmail.com", "phone": "3344827214", "tax_regime": "SIMPLIFICADO DE CONFIANZA", "cfdi_use": null, "street": null, "exterior_number": null, "interior_number": null, "neighborhood": null, "city": null, "state": null, "postal_code": null, "country": "Mexico", "fiscal_postal_code": null, "contacts": [{"name": "SAUL CORTES", "email": "saul.cortesoc@gmail.com", "phone": "3344827214"}]}	{"legal_name": "SAUL ISAAC ARCE CORTES", "commercial_name": "SAUL ISAAC ARCE CORTES", "rfc": "AECS020326TK6", "email": "saul.cortesoc@gmail.com", "phone": "3344827214", "tax_regime": "SIMPLIFICADO DE CONFIANZA", "cfdi_use": "G03", "street": null, "exterior_number": null, "interior_number": null, "neighborhood": null, "city": null, "state": null, "postal_code": null, "country": "Mexico", "fiscal_postal_code": "44950", "contacts": [{"name": "SAUL CORTES", "email": "saul.cortesoc@gmail.com", "phone": "3344827214", "position": null}]}	\N	27	2026-07-06 17:14:15.489471-06	2026-07-06 17:14:15.489471-06
\N	client.created	clients	3	null	{"legal_name": "Cliente Uno SA de CV", "rfc": "UNO010101AB1", "commercial_name": "Cliente Uno"}	\N	28	2026-07-06 17:26:53.031658-06	2026-07-06 17:26:53.031658-06
\N	client.created	clients	4	null	{"legal_name": "Cliente Dos SA de CV", "rfc": "DOS010101AB2", "commercial_name": "Cliente Dos"}	\N	29	2026-07-06 17:26:53.039207-06	2026-07-06 17:26:53.039207-06
\N	client.created	clients	5	null	{"legal_name": "METROLOGIA Y SERVICIOS MYC", "rfc": "MSM180712686", "commercial_name": "METROLOGIA Y SERVICIOS MYC"}	\N	30	2026-07-06 17:31:12.020481-06	2026-07-06 17:31:12.020481-06
\N	client.tax_constancy_uploaded	clients	5	{"tax_constancy_filename": null, "tax_constancy_path": null}	{"tax_constancy_filename": "Csf_MSM180712686.pdf", "tax_constancy_path": "clientes/cliente_5/constancia_fiscal_5df366d5ce2d423da0610e2ec3fe1375.pdf"}	\N	31	2026-07-06 17:31:12.037525-06	2026-07-06 17:31:12.037525-06
\N	client.deactivated	clients	4	{"is_active": true}	{"is_active": false}	\N	32	2026-07-06 17:31:28.643077-06	2026-07-06 17:31:28.643077-06
\N	client.deactivated	clients	3	{"is_active": true}	{"is_active": false}	\N	33	2026-07-06 17:31:31.180541-06	2026-07-06 17:31:31.180541-06
1	user.created	users	2	null	{"email": "cliente1@myc.com", "full_name": "cliente 1", "is_active": true, "role_names": ["Cliente"]}	Usuario creado desde configuracion	34	2026-07-07 10:29:27.935775-06	2026-07-07 10:29:27.935775-06
\N	service_order.created	service_orders	3	null	{"folio": "OSMYC-26-07-0003", "work_order_number": 7003, "client_id": 1, "quotation_id": 2, "status": "scheduled"}	\N	35	2026-07-07 10:30:28.811116-06	2026-07-07 10:30:28.811116-06
\N	service_order.deactivated	service_orders	3	{"is_active": true}	{"is_active": false}	\N	36	2026-07-07 10:30:52.38778-06	2026-07-07 10:30:52.38778-06
\N	client.created	clients	6	null	{"legal_name": "Industrias Atlas S.A. de C.V.", "rfc": "IAT240101AB1", "commercial_name": "Industrias Atlas"}	\N	37	2026-07-07 11:12:07.708811-06	2026-07-07 11:12:07.708811-06
\N	client.created	clients	7	null	{"legal_name": "Comercial Nova S. de R.L. de C.V.", "rfc": "CNO240215CD2", "commercial_name": "Comercial Nova"}	\N	38	2026-07-07 11:12:07.742921-06	2026-07-07 11:12:07.742921-06
\N	client.created	clients	8	null	{"legal_name": "Grupo Tecnomet S.A.P.I. de C.V.", "rfc": "GTE240320EF3", "commercial_name": "Grupo Tecnomet"}	\N	39	2026-07-07 11:12:07.756896-06	2026-07-07 11:12:07.756896-06
\N	client.deactivated	clients	1	{"is_active": true}	{"is_active": false}	\N	40	2026-07-07 11:12:36.908394-06	2026-07-07 11:12:36.908394-06
\N	client.deactivated	clients	5	{"is_active": true}	{"is_active": false}	\N	41	2026-07-07 11:12:40.202416-06	2026-07-07 11:12:40.202416-06
\N	client.created	clients	9	null	{"legal_name": "Ana Lopez Perez", "rfc": "TST114011ABC", "commercial_name": "Laboratorio Demo"}	\N	42	2026-07-07 11:40:11.120457-06	2026-07-07 11:40:11.120457-06
\N	client.updated	clients	9	{"commercial_name": "Laboratorio Demo", "municipality": "Ciudad de Mexico", "city": "Ciudad de Mexico", "legal_name": "Ana Lopez Perez"}	{"commercial_name": "Laboratorio Demo Ajustado", "municipality": "Benito Juarez", "city": "Benito Juarez", "legal_name": "Laboratorio Demo Ajustado"}	\N	43	2026-07-07 11:40:11.139177-06	2026-07-07 11:40:11.139177-06
\N	client.deactivated	clients	9	{"is_active": true}	{"is_active": false}	\N	44	2026-07-07 11:40:11.155693-06	2026-07-07 11:40:11.155693-06
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
service	calibration	Calibracion	SER-CAL-0001	Servicio de calibración a manómetro con rango de 0 - 500 psi	\N	81141504	E48	service	2100.00	MXN	1.000000	0.0000	2100.00	\N	\N	accredited_iso_17025	Servicio acreditado ISO/IEC 17025:2017	1	2026-07-06 16:22:56.407874-06	2026-07-06 16:22:56.407874-06	t	\N	\N	\N	iva_16	16.00
\.


--
-- Data for Name: certificates; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.certificates (folio, service_order_id, equipment_id, field_sheet_id, certificate_type, status, issued_on, released_on, title, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, expected_folio, final_pdf_path, final_pdf_original_filename, final_pdf_uploaded_at, final_pdf_uploaded_by_id, capture_started_at, capture_started_by_id, sent_to_quality_at, sent_to_quality_by_id, quality_reviewed_at, quality_reviewed_by_id, quality_rejection_reason, released_to_client_at, released_to_client_by_id, external_source, match_status, match_details, client_visible, authentication_code, authentication_hash, authenticated_pdf_path, authenticated_pdf_generated_at, authenticated_by_id, verification_url) FROM stdin;
MYCA-07-2026-0001	2	1	\N	acreditado	expected	2026-07-06	\N	\N	Certificado esperado generado automaticamente al dar de alta el equipo.	1	2026-07-06 16:36:29.866794-06	2026-07-06 16:36:29.866794-06	t	\N	\N	MYCA-07-2026-0001	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	excel	pending	\N	f	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: client_contacts; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.client_contacts (client_id, name, email, phone, "position", id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
2	Laura Tester	qa.cliente@example.com	5551112233	\N	2	2026-07-06 17:10:14.284347-06	2026-07-06 17:10:14.284347-06	t	\N	\N
1	SAUL CORTES	saul.cortesoc@gmail.com	3344827214	\N	4	2026-07-06 17:14:15.489471-06	2026-07-06 17:14:15.489471-06	t	\N	\N
3	Ana	uno@example.com	5551001001	\N	5	2026-07-06 17:26:53.031658-06	2026-07-06 17:26:53.031658-06	t	\N	\N
4	Luis	dos@example.com	5551001002	\N	6	2026-07-06 17:26:53.039207-06	2026-07-06 17:26:53.039207-06	t	\N	\N
6	Carlos Mendoza	carlos.mendoza@atlas.com.mx	3312345678	\N	7	2026-07-07 11:12:07.708811-06	2026-07-07 11:12:07.708811-06	t	\N	\N
7	Mariana López	mariana.lopez@nova.com.mx	3323456789	\N	8	2026-07-07 11:12:07.742921-06	2026-07-07 11:12:07.742921-06	t	\N	\N
8	Alejandro Ruiz	alejandro.ruiz@tecnomet.com.mx	3334567890	\N	9	2026-07-07 11:12:07.756896-06	2026-07-07 11:12:07.756896-06	t	\N	\N
9	Ana Lopez	test114011@example.com	5555550000	Compras	10	2026-07-07 11:40:11.120457-06	2026-07-07 11:40:11.120457-06	t	\N	\N
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.clients (legal_name, commercial_name, rfc, email, phone, tax_regime, payment_terms, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, cfdi_use, street, exterior_number, interior_number, neighborhood, city, state, postal_code, country, fiscal_postal_code, tax_constancy_filename, tax_constancy_path, tax_constancy_uploaded_at, client_type, curp, first_name, first_last_name, second_last_name, street_type, locality, municipality) FROM stdin;
Cliente Prueba QA SA de CV	Cliente Prueba QA	CPQ010101AB1	qa.cliente@example.com	5551112233	601	\N	\N	2	2026-07-06 17:10:14.284347-06	2026-07-06 17:13:39.75213-06	f	2026-07-06 17:13:39.754605-06	\N	G03	Av Demo	101	\N	Centro	CDMX	CDMX	01010	Mexico	01010	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	CDMX
Cliente Dos SA de CV	Cliente Dos	DOS010101AB2	dos@example.com	5551001002	601	\N	\N	4	2026-07-06 17:26:53.039207-06	2026-07-06 17:31:28.643077-06	f	2026-07-06 17:31:28.645978-06	\N	G03	Calle 2	20	\N	Roma	CDMX	CDMX	02020	Mexico	02020	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	CDMX
Cliente Uno SA de CV	Cliente Uno	UNO010101AB1	uno@example.com	5551001001	601	\N	\N	3	2026-07-06 17:26:53.031658-06	2026-07-06 17:31:31.180541-06	f	2026-07-06 17:31:31.185763-06	\N	G03	Calle 1	10	\N	Centro	CDMX	CDMX	01010	Mexico	01010	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	CDMX
Industrias Atlas S.A. de C.V.	Industrias Atlas	IAT240101AB1	carlos.mendoza@atlas.com.mx	3312345678	601	\N	\N	6	2026-07-07 11:12:07.708811-06	2026-07-07 11:12:07.708811-06	t	\N	\N	G03	Av. Vallarta	1540	A	Americana	Guadalajara	Jalisco	44160	México	44160	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Comercial Nova S. de R.L. de C.V.	Comercial Nova	CNO240215CD2	mariana.lopez@nova.com.mx	3323456789	601	\N	\N	7	2026-07-07 11:12:07.742921-06	2026-07-07 11:12:07.742921-06	t	\N	\N	G03	Av. Patria	890	12	Jardines Universidad	Zapopan	Jalisco	45110	México	45110	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Grupo Tecnomet S.A.P.I. de C.V.	Grupo Tecnomet	GTE240320EF3	alejandro.ruiz@tecnomet.com.mx	3334567890	601	\N	\N	8	2026-07-07 11:12:07.756896-06	2026-07-07 11:12:07.756896-06	t	\N	\N	G03	Calle Industria	245	B	El Rosario	Tlaquepaque	Jalisco	45601	México	45601	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
SAUL ISAAC ARCE CORTES	SAUL ISAAC ARCE CORTES	AECS020326TK6	saul.cortesoc@gmail.com	3344827214	SIMPLIFICADO DE CONFIANZA	\N	\N	1	2026-07-06 13:12:59.095363-06	2026-07-07 11:12:36.908394-06	f	2026-07-07 11:12:36.91111-06	\N	G03	\N	\N	\N	\N	\N	\N	\N	Mexico	44950	Csf_MSM180712686.pdf	clientes/cliente_1/constancia_fiscal_4c6b5f091cf64d8aa0e45dcf20c2868d.pdf	2026-07-06 17:13:56.629694-06	persona_moral	\N	\N	\N	\N	\N	\N	\N
METROLOGIA Y SERVICIOS MYC	METROLOGIA Y SERVICIOS MYC	MSM180712686	\N	\N	\N	\N	\N	5	2026-07-06 17:31:12.020481-06	2026-07-07 11:12:40.202416-06	f	2026-07-07 11:12:40.204799-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	45601	Csf_MSM180712686.pdf	clientes/cliente_5/constancia_fiscal_5df366d5ce2d423da0610e2ec3fe1375.pdf	2026-07-06 17:31:12.039431-06	persona_moral	\N	\N	\N	\N	\N	\N	\N
Laboratorio Demo Ajustado	Laboratorio Demo Ajustado	TST114011ABC	test114011@example.com	5555550000	612	\N	\N	9	2026-07-07 11:40:11.120457-06	2026-07-07 11:40:11.155693-06	f	2026-07-07 11:40:11.156884-06	\N	G03	Prueba	10	2	Centro	Benito Juarez	CDMX	01000	Mexico	01000	\N	\N	\N	persona_fisica	LOPA900101MDFPRN09	Ana	Lopez	Perez	Calle	Centro	Benito Juarez
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
MDG-01	Manual de Gestion de la Calidad	manual	Nivel I	\N	\N	\N	\N	\N	\N	draft	Documento semilla del nucleo documental.	\N	1	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06
FCA-02	Lista Maestra de Documentos	record	Nivel II	\N	\N	\N	\N	\N	\N	draft	Lista maestra inicial.	\N	2	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06
PMP-01	Procedimiento de uso y calibracion de manometros y vacuometros	procedure	Nivel II	\N	\N	\N	\N	\N	\N	draft	Procedimiento base para presion.	\N	3	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06
FCA-15-7	Calibracion de manometros	field_sheet_template	Nivel III	\N	\N	\N	\N	\N	\N	draft	Formato semilla de hoja de campo.	\N	4	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06
FPV-01	Orden de trabajo	work_order_template	Nivel III	\N	\N	\N	\N	\N	\N	draft	Formato semilla de orden de trabajo.	\N	5	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06
FCA-22	Cotizacion	quotation_template	Nivel III	\N	\N	\N	\N	\N	\N	draft	Formato semilla de cotizacion.	\N	6	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06
FCA-18-1	Calculo de incertidumbre	uncertainty_calculation	Nivel III	\N	\N	\N	\N	\N	\N	draft	Fuente documental para modelo de incertidumbre futuro.	\N	7	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06
\.


--
-- Data for Name: credit_notes; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.credit_notes (invoice_id, folio, issued_on, reason, subtotal, tax_total, total, status, observations, created_by_id, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
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
quotation	Plantilla de cotizacion MYC	Metrologia y Servicios MYC	Servicios de metrologia, calibracion, venta y soporte tecnico especializado.	MYC000000XXX	contacto@mycmetrology.com.mx	www.mycmetrology.com.mx			COTIZACION	Propuesta comercial de servicios, calibracion y soluciones tecnicas	FCA-23-2	\N	2025-03-28	V1	Precios expresados en moneda nacional, salvo indicacion contraria.\nVigencia sujeta a la fecha indicada en esta cotizacion.\nTiempos de entrega y alcance final se confirman al recibir autorizacion.	Los servicios metrologicos se ejecutan conforme al alcance tecnico autorizado y a la disponibilidad de patrones aplicables.	La autorizacion de esta cotizacion implica aceptacion de las condiciones comerciales, tecnicas y documentales descritas.	Los datos del cliente se usan exclusivamente para fines comerciales, operativos, documentales y de facturacion relacionados con el servicio solicitado.	Acepto las condiciones comerciales, metrologicas y legales de la presente cotizacion.	t	t	t	t	1	2026-07-06 13:13:15.727531-06	2026-07-06 13:13:15.727531-06
\.


--
-- Data for Name: equipment; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.equipment (service_order_id, service_order_item_id, status, name, brand, model, serial_number, internal_id, range_or_capacity, initial_condition, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, calibration_scope) FROM stdin;
2	1	realizing	Manometro	Winters	No disponible	3442342342	MAN-09	0 - 300 PSI	BUEN ESTADO	\N	1	2026-07-06 16:36:29.866794-06	2026-07-06 16:44:56.871259-06	t	\N	\N	accredited_iso_17025
\.


--
-- Data for Name: field_sheet_reference_standards; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheet_reference_standards (field_sheet_id, reference_standard_id, usage_role, measurement_section, notes, id, created_at, updated_at, reference_standard_certificate_id, selected_uncertainty_id, selection_status, selection_notes, validation_snapshot) FROM stdin;
\.


--
-- Data for Name: field_sheet_results; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheet_results (field_sheet_id, section_key, row_number, pattern_value, ibc_value_1, ibc_value_2, ibc_value_3, unit, notes, id, created_at, updated_at, row_data) FROM stdin;
1	dimensional_4	1	\N	\N	\N	\N	\N	\N	1	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	dimensional_4	2	\N	\N	\N	\N	\N	\N	2	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	dimensional_4	3	\N	\N	\N	\N	\N	\N	3	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	dimensional_4	4	\N	\N	\N	\N	\N	\N	4	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	dimensional_4	5	\N	\N	\N	\N	\N	\N	5	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	dimensional_4	6	\N	\N	\N	\N	\N	\N	6	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	dimensional_4	7	\N	\N	\N	\N	\N	\N	7	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	dimensional_4	8	\N	\N	\N	\N	\N	\N	8	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	dimensional_4	9	\N	\N	\N	\N	\N	\N	9	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	dimensional_4	10	\N	\N	\N	\N	\N	\N	10	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	repeatability_5	1	\N	\N	\N	\N	\N	\N	11	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	repeatability_5	2	\N	\N	\N	\N	\N	\N	12	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	repeatability_5	3	\N	\N	\N	\N	\N	\N	13	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	repeatability_5	4	\N	\N	\N	\N	\N	\N	14	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
1	repeatability_5	5	\N	\N	\N	\N	\N	\N	15	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	{}
\.


--
-- Data for Name: field_sheet_template_definitions; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheet_template_definitions (template_key, name, description, status, version, definition_json, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
general	Hoja de Campo General	\N	active	1	{"id": null, "source": "fallback", "template_key": "general", "key": "general", "name": "Hoja de Campo General", "description": null, "type": "general", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	1	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
temperatura	Hoja de Campo Temperatura	\N	active	1	{"id": null, "source": "fallback", "template_key": "temperatura", "key": "temperatura", "name": "Hoja de Campo Temperatura", "description": null, "type": "temperatura", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	2	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
termometro	Hoja de Campo Termómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "termometro", "key": "termometro", "name": "Hoja de Campo Term\\u00f3metro", "description": null, "type": "termometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	3	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
termohigrometro	Hoja de Campo Termohigrómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "termohigrometro", "key": "termohigrometro", "name": "Hoja de Campo Termohigr\\u00f3metro", "description": null, "type": "termohigrometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	4	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
transductor_presion	Hoja de Campo Transductor de Presión	\N	active	1	{"id": null, "source": "fallback", "template_key": "transductor_presion", "key": "transductor_presion", "name": "Hoja de Campo Transductor de Presi\\u00f3n", "description": null, "type": "transductor_presion", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "pressure", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "pressure_4", "block_type": "PressureTableBlock", "title": "Tabla de presi\\u00f3n", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "pressure_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "pressure_4", "title": "Tabla de presi\\u00f3n", "rows": 8, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	9	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
cronometro	Hoja de Campo Cronómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "cronometro", "key": "cronometro", "name": "Hoja de Campo Cron\\u00f3metro", "description": null, "type": "cronometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	5	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
tacometro	Hoja de Campo Tacómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "tacometro", "key": "tacometro", "name": "Hoja de Campo Tac\\u00f3metro", "description": null, "type": "tacometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	6	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
anemometro	Hoja de Campo Anemómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "anemometro", "key": "anemometro", "name": "Hoja de Campo Anem\\u00f3metro", "description": null, "type": "anemometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_anemometer_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	7	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
manometro	Hoja de Campo Manómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "manometro", "key": "manometro", "name": "Hoja de Campo Man\\u00f3metro", "description": null, "type": "manometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "pressure", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "pressure_4", "block_type": "PressureTableBlock", "title": "Tabla de presi\\u00f3n", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "pressure_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "pressure_4", "title": "Tabla de presi\\u00f3n", "rows": 8, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	8	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
valvula	Hoja de Campo Válvula	\N	active	1	{"id": null, "source": "fallback", "template_key": "valvula", "key": "valvula", "name": "Hoja de Campo V\\u00e1lvula", "description": null, "type": "valvula", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "pressure", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "pressure_4", "block_type": "PressureTableBlock", "title": "Tabla de presi\\u00f3n", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "pressure_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "pressure_4", "title": "Tabla de presi\\u00f3n", "rows": 8, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	10	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
dimensional	Hoja de Campo Dimensional	\N	active	1	{"id": null, "source": "fallback", "template_key": "dimensional", "key": "dimensional", "name": "Hoja de Campo Dimensional", "description": null, "type": "dimensional", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	11	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
regla	Hoja de Campo Regla	\N	active	1	{"id": null, "source": "fallback", "template_key": "regla", "key": "regla", "name": "Hoja de Campo Regla", "description": null, "type": "regla", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	12	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
vernier	Hoja de Campo Vernier	\N	active	1	{"id": null, "source": "fallback", "template_key": "vernier", "key": "vernier", "name": "Hoja de Campo Vernier", "description": null, "type": "vernier", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	13	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
luxometro	Hoja de Campo Luxómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "luxometro", "key": "luxometro", "name": "Hoja de Campo Lux\\u00f3metro", "description": null, "type": "luxometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	22	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
micrometro	Hoja de Campo Micrómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "micrometro", "key": "micrometro", "name": "Hoja de Campo Micr\\u00f3metro", "description": null, "type": "micrometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	14	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
flexometro	Hoja de Campo Flexómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "flexometro", "key": "flexometro", "name": "Hoja de Campo Flex\\u00f3metro", "description": null, "type": "flexometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	15	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
masa	Hoja de Campo Masa	\N	active	1	{"id": null, "source": "fallback", "template_key": "masa", "key": "masa", "name": "Hoja de Campo Masa", "description": null, "type": "masa", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "mass", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "mass_balance_4", "block_type": "MassBalanceTableBlock", "title": "Tabla masa / balanza", "visible_fields": [], "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "mass_balance_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "mass_balance_4", "title": "Tabla masa / balanza", "rows": 8, "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	16	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
balanza	Hoja de Campo Balanza	\N	active	1	{"id": null, "source": "fallback", "template_key": "balanza", "key": "balanza", "name": "Hoja de Campo Balanza", "description": null, "type": "balanza", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "mass", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "mass_balance_4", "block_type": "MassBalanceTableBlock", "title": "Tabla masa / balanza", "visible_fields": [], "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "mass_balance_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "mass_balance_4", "title": "Tabla masa / balanza", "rows": 8, "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	17	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
bascula	Hoja de Campo Báscula	\N	active	1	{"id": null, "source": "fallback", "template_key": "bascula", "key": "bascula", "name": "Hoja de Campo B\\u00e1scula", "description": null, "type": "bascula", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "mass", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "mass_balance_4", "block_type": "MassBalanceTableBlock", "title": "Tabla masa / balanza", "visible_fields": [], "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "mass_balance_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "mass_balance_4", "title": "Tabla masa / balanza", "rows": 8, "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	18	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
peso_patron	Hoja de Campo Peso Patrón	\N	active	1	{"id": null, "source": "fallback", "template_key": "peso_patron", "key": "peso_patron", "name": "Hoja de Campo Peso Patr\\u00f3n", "description": null, "type": "peso_patron", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "mass", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "mass_balance_4", "block_type": "MassBalanceTableBlock", "title": "Tabla masa / balanza", "visible_fields": [], "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "mass_balance_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "mass_balance_4", "title": "Tabla masa / balanza", "rows": 8, "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	19	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
electrica	Hoja de Campo Eléctrica	\N	active	1	{"id": null, "source": "fallback", "template_key": "electrica", "key": "electrica", "name": "Hoja de Campo El\\u00e9ctrica", "description": null, "type": "electrica", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 2, "pdf_template": "field_sheet_electrical_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "electrical", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "electrical_4", "block_type": "ElectricalTableBlock", "title": "Tabla el\\u00e9ctrica", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [{"key": "voltage_ac", "title": "Voltaje AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "voltage_dc", "title": "Voltaje DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_ac", "title": "Corriente AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_dc", "title": "Corriente DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "resistance", "title": "Resistencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "frequency", "title": "Frecuencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "continuity", "title": "Continuidad", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "electrical_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "sectioned_5", "block_type": "SectionedTableBlock", "title": "Secciones personalizadas", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [{"key": "custom_section", "title": "Secci\\u00f3n personalizada", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "sectioned_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "voltage_ac", "title": "Voltaje AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "voltage_dc", "title": "Voltaje DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_ac", "title": "Corriente AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_dc", "title": "Corriente DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "resistance", "title": "Resistencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "frequency", "title": "Frecuencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "continuity", "title": "Continuidad", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "custom_section", "title": "Secci\\u00f3n personalizada", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	20	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
multimetro	Hoja de Campo Multímetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "multimetro", "key": "multimetro", "name": "Hoja de Campo Mult\\u00edmetro", "description": null, "type": "multimetro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "electrical", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "electrical_4", "block_type": "ElectricalTableBlock", "title": "Tabla el\\u00e9ctrica", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [{"key": "voltage_ac", "title": "Voltaje AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "voltage_dc", "title": "Voltaje DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_ac", "title": "Corriente AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_dc", "title": "Corriente DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "resistance", "title": "Resistencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "frequency", "title": "Frecuencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "continuity", "title": "Continuidad", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "electrical_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "sectioned_5", "block_type": "SectionedTableBlock", "title": "Secciones personalizadas", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [{"key": "custom_section", "title": "Secci\\u00f3n personalizada", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "sectioned_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "voltage_ac", "title": "Voltaje AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "voltage_dc", "title": "Voltaje DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_ac", "title": "Corriente AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_dc", "title": "Corriente DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "resistance", "title": "Resistencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "frequency", "title": "Frecuencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "continuity", "title": "Continuidad", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "custom_section", "title": "Secci\\u00f3n personalizada", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	21	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
sonido	Hoja de Campo Sonido	\N	active	1	{"id": null, "source": "fallback", "template_key": "sonido", "key": "sonido", "name": "Hoja de Campo Sonido", "description": null, "type": "sonido", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	23	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
sonometro	Hoja de Campo Sonómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "sonometro", "key": "sonometro", "name": "Hoja de Campo Son\\u00f3metro", "description": null, "type": "sonometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	24	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
torquimetro	Hoja de Campo Torquímetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "torquimetro", "key": "torquimetro", "name": "Hoja de Campo Torqu\\u00edmetro", "description": null, "type": "torquimetro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	25	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
dinamometro	Hoja de Campo Dinamómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "dinamometro", "key": "dinamometro", "name": "Hoja de Campo Dinam\\u00f3metro", "description": null, "type": "dinamometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	26	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
durometro	Hoja de Campo Durómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "durometro", "key": "durometro", "name": "Hoja de Campo Dur\\u00f3metro", "description": null, "type": "durometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	27	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
volumen	Hoja de Campo Volumen	\N	active	1	{"id": null, "source": "fallback", "template_key": "volumen", "key": "volumen", "name": "Hoja de Campo Volumen", "description": null, "type": "volumen", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	28	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
\.


--
-- Data for Name: field_sheets; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheets (equipment_id, status, initial_condition, final_condition, pattern_used, results, observations, evidence_notes, method, environmental_conditions, technician_notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, template_key, work_order_number, calibration_place, reception_date, calibration_date, next_calibration_date, environment_humidity_start, environment_humidity_end, environment_temperature_start, environment_temperature_end, equipment_general_condition, consider_equipment_deviations, units, calibrated_by, reviewed_by, report_made_by, purchase_order_or_quotation, calibration_procedure_id, returned_to_technician_at, returned_to_technician_by_id, returned_to_technician_reason, certificate_client_mode, certificate_client_company, certificate_client_attention, certificate_client_address, apply_certificate_client_to_order, minimum_division, location, attention, company, address, template_definition_json, template_definition_version) FROM stdin;
1	draft	\N	\N	\N	\N	\N	\N	\N	\N	\N	1	2026-07-06 16:45:45.201869-06	2026-07-06 16:45:45.201869-06	t	\N	\N	micrometro	7002	\N	2026-07-06	2026-07-07	\N	\N	\N	\N	\N	\N	f	\N	\N	\N	\N	MYC-07-26-0002	\N	\N	\N	\N	billing	\N	\N	\N	t	\N	\N	\N	\N	\N	{"id": 14, "source": "database", "template_key": "micrometro", "key": "micrometro", "name": "Hoja de Campo Micr\\u00f3metro", "description": null, "type": "micrometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	1
\.


--
-- Data for Name: invoice_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.invoice_items (invoice_id, quotation_item_id, certificate_id, equipment_id, description, quantity, unit, sat_unit, sat_key, unit_price, discount_total, tax_rate, tax_total, line_total, notes, service_type, source_type, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: invoice_payments; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.invoice_payments (invoice_id, paid_on, amount, bank_name, bank_account, reference, payment_method, payment_form, status, notes, registered_by_id, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: invoice_settings; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.invoice_settings (key, default_series, next_sequence, reset_annually, default_tax_rate, default_currency, default_credit_days, allow_manual_folio, forms_of_payment, methods_of_payment, usage_cfdi_catalog, tax_regime_catalog, currency_catalog, sat_product_keys, sat_units, banks, bank_accounts, legal_texts, billing_emails, emitter_data, pdf_template_name, cfdi_future_parameters, id, created_at, updated_at) FROM stdin;
default	F	1	f	16.00	MXN	0	f	{"items": ["Transferencia", "Efectivo", "Tarjeta", "Cheque"]}	{"items": ["PUE", "PPD"]}	{"items": ["G03", "P01"]}	{"items": ["601", "603", "612"]}	{"items": ["MXN", "USD"]}	{"items": ["81141504", "84111506"]}	{"items": ["E48", "ACT"]}	{"items": ["BBVA", "Banamex", "Santander"]}	{"items": []}	{"invoice_legend": "Documento administrativo interno, no CFDI timbrado"}	{"items": ["cobranza@myc.com.mx"]}	{"commercial_name": "MYC SYSTEM", "legal_name": "METROLOGIA Y SERVICIOS MYC", "rfc": "", "tax_regime": "", "postal_code": "", "address": "", "email": "", "phone": "", "place_of_issue": ""}	invoice_pdf.html	{}	1	2026-07-06 15:45:43.614805-06	2026-07-06 15:45:43.614805-06
\.


--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.invoices (internal_uuid, series, folio, client_id, fiscal_client_id, service_order_id, quotation_id, issued_on, due_on, subtotal, tax_total, withholding_total, discount_total, total, balance_due, amount_paid, status, payment_method, payment_form, usage_cfdi, currency, credit_days, observations, internal_comments, cancellation_reason, created_by_id, updated_by_id, last_payment_on, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: quotation_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.quotation_items (quotation_id, service_name, description, quantity, unit_price, total, id, created_at, updated_at, is_active, deleted_at, deleted_by, catalog_item_id, unit, currency, commodity, calibration_scope, quotation_legend, sat_key, sat_unit, internal_unit, discount_percent, tax_object, tax_rate, tax_total) FROM stdin;
2	Servicio de calibración a manómetro con rango de 0 - 500 psi	\N	1	2100.00	2100.00	1	2026-07-06 16:31:37.406952-06	2026-07-06 16:31:37.406952-06	t	\N	\N	1	service	MXN	calibration	accredited_iso_17025	Servicio acreditado ISO/IEC 17025:2017	81141504	E48	service	0.0000	iva_16	16.00	336.00
\.


--
-- Data for Name: quotations; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.quotations (folio, client_id, status, issued_on, valid_until, subtotal, tax_total, total, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, advisor_id) FROM stdin;
MYC-07-26-0001	1	accepted	2026-07-06	\N	0.00	0.00	0.00	\N	1	2026-07-06 16:24:47.201901-06	2026-07-06 16:31:10.703092-06	f	2026-07-06 16:31:10.705668-06	\N	\N
MYC-07-26-0002	1	accepted	2026-07-06	\N	2100.00	336.00	2436.00	\N	2	2026-07-06 16:31:30.354774-06	2026-07-06 16:33:42.439395-06	t	\N	\N	\N
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
Administrador	Acceso total al sistema.	1	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
Comercial	Gestion comercial, clientes y cotizaciones.	2	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
Tecnico	Gestion tecnica de equipos y hojas de campo.	3	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
Captura	Captura y generacion documental.	4	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
Calidad	Revision y aprobacion de certificados.	5	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
Finanzas	Pagos, facturacion y liberacion financiera.	6	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
Cliente	Acceso limitado para cliente externo.	7	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06	t	\N	\N
Desarrollador	Acceso tecnico avanzado para desarrollo y soporte.	8	2026-07-06 12:48:46.001288-06	2026-07-06 12:48:46.001288-06	t	\N	\N
\.


--
-- Data for Name: service_order_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.service_order_items (service_order_id, quotation_item_id, service_name, quantity, status, id, created_at, updated_at, is_active, deleted_at, deleted_by, calibration_scope) FROM stdin;
2	1	Servicio de calibración a manómetro con rango de 0 - 500 psi	1	pending	1	2026-07-06 16:33:44.766109-06	2026-07-06 16:33:44.766109-06	t	\N	\N	accredited_iso_17025
3	1	Servicio de calibración a manómetro con rango de 0 - 500 psi	1	pending	2	2026-07-07 10:30:28.811116-06	2026-07-07 10:30:28.811116-06	t	\N	\N	accredited_iso_17025
\.


--
-- Data for Name: service_orders; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.service_orders (folio, client_id, quotation_id, status, agenda_date, closed_at, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, advisor_id, technician_id, service_date, total_equipment, completed_equipment, requires_payment, work_order_number) FROM stdin;
OSMYC-26-07-0001	1	1	scheduled	\N	\N	Generada desde cotizacion MYC-07-26-0001	1	2026-07-06 16:30:03.199625-06	2026-07-06 16:31:14.788937-06	f	2026-07-06 16:31:14.805136-06	\N	\N	\N	\N	0	0	t	7001
OSMYC-26-07-0002	1	2	called	2026-07-06	\N	Generada desde cotizacion MYC-07-26-0002	2	2026-07-06 16:33:44.766109-06	2026-07-06 16:36:29.912708-06	t	\N	\N	\N	\N	2026-07-07	1	0	t	7002
OSMYC-26-07-0003	1	2	scheduled	\N	\N	Generada desde cotizacion MYC-07-26-0002	3	2026-07-07 10:30:28.811116-06	2026-07-07 10:30:52.38778-06	f	2026-07-07 10:30:52.393357-06	\N	\N	\N	\N	0	0	t	7003
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
PT-PRESION-MANOMETRO-ACR-001	Perfil Tecnico Presion - Manometros Acreditado	Presion	Manometro	calibration	accredited	\N	\N	\N	\N	\N	draft	1	\N	Perfil semilla; no contiene calculos metrologicos.	\N	\N	\N	1	2026-07-06 12:48:02.376142-06	2026-07-06 12:48:02.376142-06
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
2	7
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.users (email, full_name, hashed_password, role_id, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
saul@myc.com	admin	$pbkdf2-sha256$29000$IqRUSklp7Z2zds6Z0zoHIA$PSAwHm5iGWOmIhpBtkRJ3pLMYRpqk8PMd7eXigC1bJ8	1	1	2026-07-06 12:48:46.001288-06	2026-07-06 12:48:46.001288-06	t	\N	\N
cliente1@myc.com	cliente 1	$pbkdf2-sha256$29000$VsqZM2as1do7B6B0zhkDYA$ZcBz3HElIpbv.4KVuLI7j.AL.w6YnV6jotRzjJIxPDE	7	2	2026-07-07 10:29:27.935775-06	2026-07-07 10:29:27.935775-06	t	\N	\N
\.


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 44, true);


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

SELECT pg_catalog.setval('public.certificates_id_seq', 1, true);


--
-- Name: client_contacts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.client_contacts_id_seq', 10, true);


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.clients_id_seq', 9, true);


--
-- Name: controlled_document_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.controlled_document_versions_id_seq', 1, false);


--
-- Name: controlled_documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.controlled_documents_id_seq', 7, true);


--
-- Name: credit_notes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.credit_notes_id_seq', 1, false);


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

SELECT pg_catalog.setval('public.equipment_id_seq', 1, true);


--
-- Name: field_sheet_reference_standards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheet_reference_standards_id_seq', 1, false);


--
-- Name: field_sheet_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheet_results_id_seq', 15, true);


--
-- Name: field_sheet_template_definitions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheet_template_definitions_id_seq', 28, true);


--
-- Name: field_sheets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheets_id_seq', 1, true);


--
-- Name: invoice_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.invoice_items_id_seq', 1, false);


--
-- Name: invoice_payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.invoice_payments_id_seq', 1, false);


--
-- Name: invoice_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.invoice_settings_id_seq', 1, true);


--
-- Name: invoices_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.invoices_id_seq', 1, false);


--
-- Name: quotation_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.quotation_items_id_seq', 1, true);


--
-- Name: quotations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.quotations_id_seq', 2, true);


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

SELECT pg_catalog.setval('public.service_order_items_id_seq', 2, true);


--
-- Name: service_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.service_orders_id_seq', 3, true);


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

SELECT pg_catalog.setval('public.users_id_seq', 2, true);


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
-- Name: credit_notes credit_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.credit_notes
    ADD CONSTRAINT credit_notes_pkey PRIMARY KEY (id);


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
-- Name: field_sheet_template_definitions field_sheet_template_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_template_definitions
    ADD CONSTRAINT field_sheet_template_definitions_pkey PRIMARY KEY (id);


--
-- Name: field_sheets field_sheets_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets
    ADD CONSTRAINT field_sheets_pkey PRIMARY KEY (id);


--
-- Name: invoice_items invoice_items_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_pkey PRIMARY KEY (id);


--
-- Name: invoice_payments invoice_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_payments
    ADD CONSTRAINT invoice_payments_pkey PRIMARY KEY (id);


--
-- Name: invoice_settings invoice_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_settings
    ADD CONSTRAINT invoice_settings_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


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
-- Name: field_sheet_template_definitions uq_field_sheet_template_key_version; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_template_definitions
    ADD CONSTRAINT uq_field_sheet_template_key_version UNIQUE (template_key, version);


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
-- Name: ix_clients_client_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_client_type ON public.clients USING btree (client_type);


--
-- Name: ix_clients_commercial_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_commercial_name ON public.clients USING btree (commercial_name);


--
-- Name: ix_clients_curp; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_curp ON public.clients USING btree (curp);


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
-- Name: ix_credit_notes_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_credit_notes_folio ON public.credit_notes USING btree (folio);


--
-- Name: ix_credit_notes_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_credit_notes_id ON public.credit_notes USING btree (id);


--
-- Name: ix_credit_notes_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_credit_notes_status ON public.credit_notes USING btree (status);


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
-- Name: ix_equipment_calibration_scope; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_calibration_scope ON public.equipment USING btree (calibration_scope);


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
-- Name: ix_field_sheet_template_definitions_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_template_definitions_id ON public.field_sheet_template_definitions USING btree (id);


--
-- Name: ix_field_sheet_template_definitions_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_template_definitions_status ON public.field_sheet_template_definitions USING btree (status);


--
-- Name: ix_field_sheet_template_definitions_template_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_template_definitions_template_key ON public.field_sheet_template_definitions USING btree (template_key);


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
-- Name: ix_invoice_items_certificate_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_items_certificate_id ON public.invoice_items USING btree (certificate_id);


--
-- Name: ix_invoice_items_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_items_id ON public.invoice_items USING btree (id);


--
-- Name: ix_invoice_items_invoice_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_items_invoice_id ON public.invoice_items USING btree (invoice_id);


--
-- Name: ix_invoice_items_source_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_items_source_type ON public.invoice_items USING btree (source_type);


--
-- Name: ix_invoice_payments_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_payments_id ON public.invoice_payments USING btree (id);


--
-- Name: ix_invoice_payments_invoice_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_payments_invoice_id ON public.invoice_payments USING btree (invoice_id);


--
-- Name: ix_invoice_payments_reference; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_payments_reference ON public.invoice_payments USING btree (reference);


--
-- Name: ix_invoice_payments_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_payments_status ON public.invoice_payments USING btree (status);


--
-- Name: ix_invoice_settings_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_settings_id ON public.invoice_settings USING btree (id);


--
-- Name: ix_invoice_settings_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_invoice_settings_key ON public.invoice_settings USING btree (key);


--
-- Name: ix_invoices_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_invoices_folio ON public.invoices USING btree (folio);


--
-- Name: ix_invoices_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoices_id ON public.invoices USING btree (id);


--
-- Name: ix_invoices_internal_uuid; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_invoices_internal_uuid ON public.invoices USING btree (internal_uuid);


--
-- Name: ix_invoices_series; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoices_series ON public.invoices USING btree (series);


--
-- Name: ix_invoices_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoices_status ON public.invoices USING btree (status);


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
-- Name: credit_notes credit_notes_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.credit_notes
    ADD CONSTRAINT credit_notes_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: credit_notes credit_notes_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.credit_notes
    ADD CONSTRAINT credit_notes_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


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
-- Name: invoice_items invoice_items_certificate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_certificate_id_fkey FOREIGN KEY (certificate_id) REFERENCES public.certificates(id);


--
-- Name: invoice_items invoice_items_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id);


--
-- Name: invoice_items invoice_items_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: invoice_items invoice_items_quotation_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_quotation_item_id_fkey FOREIGN KEY (quotation_item_id) REFERENCES public.quotation_items(id);


--
-- Name: invoice_payments invoice_payments_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_payments
    ADD CONSTRAINT invoice_payments_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: invoice_payments invoice_payments_registered_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_payments
    ADD CONSTRAINT invoice_payments_registered_by_id_fkey FOREIGN KEY (registered_by_id) REFERENCES public.users(id);


--
-- Name: invoices invoices_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: invoices invoices_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: invoices invoices_fiscal_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_fiscal_client_id_fkey FOREIGN KEY (fiscal_client_id) REFERENCES public.clients(id);


--
-- Name: invoices invoices_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.quotations(id);


--
-- Name: invoices invoices_service_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_service_order_id_fkey FOREIGN KEY (service_order_id) REFERENCES public.service_orders(id);


--
-- Name: invoices invoices_updated_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_updated_by_id_fkey FOREIGN KEY (updated_by_id) REFERENCES public.users(id);


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
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict L777Ft5y1CFUHNBar3KAMQtWjAEI0bNxzzNBPDuyAMckAX87U6R39VQCxtvV5DF

