"""Conteúdo de SEO por página, aplicado por tools/seo.py.

Para mudar título, description, H1 ou textos de uma página, edite aqui e rode:
    python tools/seo.py
"""

BASE = "https://axxiscontabilidade.com.br"
HERO_SUB_DEFAULT = "Foco nas necessidades de negócios de nossos clientes"
ORANGE = '<span style="color: #ff6d00">{}</span>'
HIGHLIGHT = '<span class="highlight">{}</span>'

# Páginas em que nenhuma palavra existente é alterada (só ajustes técnicos)
LOCKED = {"empresas-do-fitness"}

ORG = {
    "name": "Axxis Contabilidade Consultiva",
    "alternateName": "AXXIS Contabilidade",
    "description": "Contabilidade consultiva com tecnologia: gestão contábil e fiscal, departamento pessoal, planejamento tributário e BPO para empresas de diversos segmentos.",
    "logo": "/wp-content/uploads/2025/08/cropped-Logo-Antiga-Axxis-1080-x-1350-px-2.png",
    "telephone": "+55-61-98188-2247",
    "email": "contato@grupoaxxis.com.br",
    "taxID": "33.354.692/0001-25",
    "address": {
        "streetAddress": "Ed. Connect Towers, QS 1, Rua 212, Bloco D, 8º andar, Sala 804",
        "addressLocality": "Brasília",
        "addressRegion": "DF",
        "postalCode": "71950-550",
        "addressCountry": "BR",
    },
    "sameAs": [
        "https://www.instagram.com/axxiscontabilidade/",
        "https://br.linkedin.com/company/axxis-contabilidade",
        "https://www.facebook.com/axxiscontabilidadeconsultiva",
    ],
    "parent": {"name": "Grupo Axxis", "url": "https://grupoaxxis.com.br"},
}

# Substituições aplicadas em todas as páginas (exceto LOCKED)
GLOBAL_REPLACE = [
    ("ERP</span> , sistema", "ERP</span>, sistema"),
]

# alt para imagens sem texto alternativo (chave = trecho do nome do arquivo)
ALTS = {
    "sala-de-aula-virtual-e-espaco-de-estudo": "Criadora de conteúdo gravando vídeo com smartphone",
    "reporter-de-imprensa-que-segue-pistas": "Equipe de produção audiovisual reunida em um projeto",
    "medico-hispanico-conversando-com-uma-paciente": "Médico atendendo paciente no consultório",
    "natural__18412": "Profissional analisando relatórios financeiros no computador",
    "vista-lateral-pessoas-treinando-juntas-na-academia": "Alunos treinando em bicicletas ergométricas na academia",
    "pessoas-em-forma-treinando-juntos": "Pessoas se alongando em academia com esteiras ao fundo",
    "mulherocupada": "Contadora analisando gráficos financeiros no computador",
    "mulher-de-tiro-medio-segurando-tablet": "Profissional consultando indicadores financeiros no tablet",
    "mulher-de-vista-superior-digitando-no-laptop": "Mãos digitando em notebook com planilha e calculadora",
    "natural__41887": "Consultor apresentando gráficos de desempenho em tela digital",
    "vista-frontal-de-uma-mulher-segurando-uma-prancheta": "Profissional revisando documentos em prancheta",
    "pessoa-no-escritorio-analisando-e-verificando-graficos-financeiros-1": "Executiva analisando gráficos financeiros no tablet",
    "close-up-homem-de-negocios-com-tabuleta-digital": "Análise de relatórios financeiros em tablet durante reunião",
    "equipe-de-negocios-de-tiro-medio-trabalhando": "Equipe de negócios analisando resultados em reunião",
    "natural__41889": "Profissional acompanhando indicadores financeiros no computador",
    "laboratorio-de-informatica-moderno-e-equipado": "Equipe de empresa de tecnologia trabalhando com dashboards",
    "/2025/08/5.png": "Colaborador da equipe Axxis",
    "/2025/08/2.png": "Colaboradora da equipe Axxis com notebook",
}

SERVICOS = ("nossas-solucoes", "Nossas Soluções")
SETORES = ("areas-de-atuacao", "Áreas de Atuação")

# kind: home | about | service | sector | legal | page
# h1: novo conteúdo do primeiro H1; sub: novo subtítulo do banner; replace: (antigo, novo)
# demote: H1 secundário que vira H2, com o seletor CSS que o estiliza (antigo, novo)
PAGES = {
    "": {
        "kind": "home", "name": "Início",
        "title": "Contabilidade Consultiva em Brasília (DF) | Axxis",
        "description": "Contabilidade consultiva em Brasília e para empresas de todo o país: gestão contábil e fiscal, departamento pessoal, planejamento tributário e BPO.",
        "og_image": "/wp-content/uploads/al_opt_content/IMAGE/axxiscontabilidade.com.br/wp-content/uploads/2025/08/hero-_1_-1-scaled-e1755018203362.webp",
    },
    "sobre-nos": {
        "kind": "about", "name": "Sobre Nós",
        "title": "Sobre a Axxis | Contabilidade Consultiva",
        "description": "Conheça a Axxis: contadores e especialistas em tecnologia que transformam a contabilidade em ferramenta estratégica para o crescimento da sua empresa.",
        "h1": "Sobre a " + ORANGE.format("Axxis"),
        "sub": "Contadores e especialistas em tecnologia a serviço do seu crescimento",
        "insert_after": [(
            r"impulsionam seu sucesso\.\s*</p>",
            '<p>Com sede em Águas Claras, em Brasília (DF), atendemos empresas da capital e de outros estados. '
            'Já são mais de 700 empresas atendidas, mais de 5.000 folhas de pagamento processadas por mês e '
            'R$ 1,2 bilhão em ativos sob gestão, com serviços que vão da '
            '<a href="/gestao-contabil-e-fiscal/">gestão contábil e fiscal</a> ao '
            '<a href="/departamento-pessoal/">departamento pessoal</a>, '
            '<a href="/planejamento-tributario/">planejamento tributário</a> e '
            '<a href="/bpo-financeiro/">BPO financeiro</a>.</p>',
        )],
        "css": ".axxis-about-history-section .history-text p a{color:#ff6d00;text-decoration:none}",
    },
    "nossas-solucoes": {
        "kind": "page", "name": "Nossas Soluções",
        "title": "Serviços de Contabilidade e BPO para Empresas | Axxis",
        "description": "Gestão contábil e fiscal, departamento pessoal, planejamento tributário e BPO financeiro integrados ao seu ERP. Conheça as soluções da Axxis.",
        "h1": "Soluções em " + ORANGE.format("Contabilidade e BPO"),
        "replace": [
            ("oportunidadese otimizar", "oportunidades e otimizar"),
            ("reuniões Periódica para", "reuniões periódicas para"),
            ("resultar em em menos", "resultar em menos"),
            (">Reestruturação Fiscal e Societária<", ">Vocês fazem reestruturação fiscal e societária?<"),
            (">Consultoria Contábil Periódica<", ">Como funciona a consultoria contábil periódica?<"),
        ],
    },
    "abrir-empresa": {
        "kind": "service", "name": "Abrir Empresa", "parent": SERVICOS, "service": "Abertura de empresa",
        "title": "Abrir Empresa em Brasília (DF) sem Burocracia | Axxis",
        "description": "Abra seu CNPJ 100% online: diagnóstico, contrato social, Junta Comercial e inscrições fiscais. Abertura gratuita na contratação do plano anual.",
        "sub": "Do diagnóstico ao CNPJ ativo, 100% online",
        "demote": [(r"<h1>Abra seu CNPJ", ".axxis-hero-abertura h1", ".axxis-hero-abertura h2")],
    },
    "trabalhe-conosco": {
        "kind": "page", "name": "Trabalhe Conosco",
        "title": "Trabalhe Conosco | Carreiras no Grupo Axxis",
        "description": "Faça parte do Grupo Axxis: projetos desafiadores, tecnologia no dia a dia e um time que investe no seu crescimento. Envie seu currículo.",
        "h1": "Trabalhe " + ORANGE.format("conosco"),
        "sub": "Cresça com um time que investe em tecnologia e pessoas",
        "demote": [(r"<h1>Bem-vindo", ".axxis-team-intro-text h1", ".axxis-team-intro-text h2")],
        "insert_after": [(
            r"desenvolvimento de cada talento\.\s*</p>",
            "<p>Nossas equipes atuam em contabilidade, área fiscal, departamento pessoal, BPO financeiro e "
            "tecnologia, atendendo empresas de diversos segmentos a partir da nossa sede em Brasília (DF).</p>",
        )],
    },
    "areas-de-atuacao": {
        "kind": "page", "name": "Áreas de Atuação",
        "title": "Contabilidade Especializada por Setor | Axxis",
        "description": "Contabilidade consultiva para Simples Nacional, Lucro Real e Presumido, saúde, startups, construção civil, ensino, agências, fundos e academias.",
        "h1": "Contabilidade especializada " + ORANGE.format("por setor"),
        "sub": "Soluções contábeis sob medida para cada segmento",
    },
    "gestao-contabil-e-fiscal": {
        "kind": "service", "name": "Gestão Contábil e Fiscal", "parent": SERVICOS, "service": "Gestão contábil e fiscal",
        "title": "Gestão Contábil e Fiscal para Empresas | Axxis",
        "description": "Contabilidade e obrigações fiscais em dia, com revisão rigorosa, compliance e recuperação de impostos. Gestão contábil e fiscal completa.",
    },
    "departamento-pessoal": {
        "kind": "service", "name": "Departamento Pessoal", "parent": SERVICOS, "service": "Departamento pessoal e folha de pagamento",
        "title": "Departamento Pessoal e Folha de Pagamento | Axxis",
        "description": "Terceirize o departamento pessoal: folha de pagamento, admissões, férias, rescisões e eSocial com conformidade total e sem riscos trabalhistas.",
    },
    "planejamento-tributario": {
        "kind": "service", "name": "Planejamento Tributário", "parent": SERVICOS, "service": "Planejamento tributário",
        "title": "Planejamento Tributário: Pague Menos Impostos | Axxis",
        "description": "Reduza impostos de forma legal: análise de regime (Simples, Presumido ou Real), recuperação de créditos e incentivos fiscais para sua empresa.",
    },
    "bpo-financeiro": {
        "kind": "service", "name": "BPO Financeiro", "parent": SERVICOS, "service": "BPO financeiro",
        "title": "BPO Financeiro: Terceirização Financeira | Axxis",
        "description": "Terceirize contas a pagar e receber, conciliação bancária, fluxo de caixa e relatórios com especialistas, por menos que uma equipe interna.",
        "sub": "Rotinas financeiras nas mãos de especialistas",
    },
    "bpo-de-rh": {
        "kind": "service", "name": "BPO de RH", "parent": SERVICOS, "service": "BPO de RH",
        "title": "BPO de RH: Terceirização do Departamento Pessoal | Axxis",
        "description": "Terceirize a rotina de RH e departamento pessoal: folha, benefícios, admissões, rescisões e eSocial com conformidade e menor custo.",
        "h1": "BPO de RH: transforme seu RH em um pilar " + HIGHLIGHT.format("estratégico"),
        "sub": "Folha, benefícios e eSocial com especialistas",
    },
    "bpo-juridico": {
        "kind": "service", "name": "BPO Jurídico", "parent": SERVICOS, "service": "BPO jurídico",
        "title": "BPO Jurídico: Contratos e Societário | Axxis",
        "description": "Terceirize a gestão de contratos, atos societários e rotinas legais da sua empresa com segurança, conformidade e confidencialidade.",
        "h1": "BPO Jurídico: seu jurídico organizado, seguro e " + HIGHLIGHT.format("ágil"),
    },
    "bpo-de-licitacoes-e-contratos": {
        "kind": "service", "name": "BPO de Licitações", "parent": SERVICOS, "service": "BPO de licitações e contratos públicos",
        "title": "BPO de Licitações e Contratos Públicos | Axxis",
        "description": "Da análise do edital à gestão do contrato: cuidamos de documentos, cadastros, propostas e lances em pregões para sua empresa vender ao governo.",
        "h1": "BPO de Licitações: conquiste contratos públicos com segurança e " + HIGHLIGHT.format("estratégia"),
        "sub": "Da análise do edital à gestão do contrato",
    },
    "gestor-estrategico-financeiro": {
        "kind": "service", "name": "Gestor Estratégico Financeiro", "parent": SERVICOS, "service": "Gestão estratégica financeira (controller)",
        "title": "Gestor Estratégico Financeiro (Controller) | Axxis",
        "description": "Um controller dedicado à sua empresa: KPIs, fluxo de caixa, DRE, relatórios gerenciais e planejamento financeiro para decidir com segurança.",
        "h1": "Gestor Estratégico Financeiro: decisões inteligentes, crescimento " + HIGHLIGHT.format("sustentável"),
        "sub": "Um controller dedicado ao crescimento do seu negócio",
    },
    "simples-nacional": {
        "kind": "sector", "name": "Simples Nacional", "parent": SETORES, "service": "Contabilidade para empresas do Simples Nacional",
        "title": "Contabilidade para Simples Nacional e Fator R | Axxis",
        "description": "Pague menos no Simples Nacional: planejamento do Fator R, segregação de receitas monofásicas e com ST e controle do limite de faturamento.",
        "h1": "Contabilidade para " + ORANGE.format("Simples Nacional"),
        "sub": "Menos impostos com Fator R e segregação correta de receitas",
    },
    "lucro-real-e-presumido": {
        "kind": "sector", "name": "Lucro Real e Presumido", "parent": SETORES, "service": "Contabilidade para Lucro Real e Lucro Presumido",
        "title": "Contabilidade para Lucro Real e Presumido | Axxis",
        "description": "Escolha o regime mais vantajoso entre Lucro Real e Presumido, com SPED e ECF em dia e recuperação de créditos de PIS/COFINS.",
        "h1": "Contabilidade para " + ORANGE.format("Lucro Real e Presumido"),
        "sub": "Regime certo, créditos recuperados e SPED em dia",
    },
    "empresas-da-saude": {
        "kind": "sector", "name": "Empresas da Saúde", "parent": SETORES, "service": "Contabilidade para médicos, clínicas e consultórios",
        "title": "Contabilidade para Médicos e Clínicas | Axxis",
        "description": "Contabilidade para médicos, dentistas e clínicas: PF ou PJ, Carnê-Leão, glosas de convênios e repasse médico com menor carga tributária.",
        "h1": "Contabilidade para a " + ORANGE.format("Área da Saúde"),
        "sub": "Menos impostos e mais organização para clínicas e consultórios",
    },
    "agencias-e-midia": {
        "kind": "sector", "name": "Agências e Mídia", "parent": SETORES, "service": "Contabilidade para agências de publicidade e mídia",
        "title": "Contabilidade para Agências de Publicidade | Axxis",
        "description": "Contabilidade para agências e produtoras: rentabilidade por cliente e projeto, ISS, retenções na nota e fluxo de caixa sob controle.",
        "h1": "Contabilidade para " + ORANGE.format("Agências e Mídia"),
        "sub": "Rentabilidade por cliente e tributação correta para sua agência",
    },
    "fundos-de-investimentos-e-sas": {
        "kind": "sector", "name": "Fundos de Investimento e S/As", "parent": SETORES, "service": "Contabilidade para fundos de investimento e sociedades anônimas",
        "title": "Contabilidade para Fundos de Investimento e S/A | Axxis",
        "description": "Contabilidade para fundos e sociedades anônimas: normas da CVM, governança, apuração de cotas, marcação a mercado e dividendos.",
        "h1": "Contabilidade para " + ORANGE.format("Fundos de Investimento e S/As"),
        "sub": "Governança e conformidade para fundos e sociedades anônimas",
    },
    "incorporadoras-e-engenharias": {
        "kind": "sector", "name": "Incorporadoras e Engenharias", "parent": SETORES, "service": "Contabilidade para incorporadoras, construtoras e engenharias",
        "title": "Contabilidade para Construtoras e Incorporadoras | Axxis",
        "description": "Contabilidade para construção civil: RET, gestão de SPEs, patrimônio de afetação e custos por obra (CNO) para proteger sua margem.",
        "h1": "Contabilidade para " + ORANGE.format("Incorporadoras e Engenharias"),
        "sub": "RET, SPEs e custos por obra sob controle",
    },
    "instituicoes-de-ensino": {
        "kind": "sector", "name": "Instituições de Ensino", "parent": SETORES, "service": "Contabilidade para escolas e instituições de ensino",
        "title": "Contabilidade para Escolas e Faculdades | Axxis",
        "description": "Contabilidade para instituições de ensino: mensalidades e inadimplência, folha de professores, PROUNI, FIES, CEBAS e imunidades.",
        "h1": "Contabilidade para " + ORANGE.format("Instituições de Ensino"),
        "sub": "Mensalidades, folha docente e benefícios fiscais em ordem",
    },
    "startups-e-tecnologias": {
        "kind": "sector", "name": "Startups e Tecnologia", "parent": SETORES, "service": "Contabilidade para startups e empresas de tecnologia",
        "title": "Contabilidade para Startups e SaaS | Axxis",
        "description": "Contabilidade para startups e SaaS: valuation, cap table, stock options, receita recorrente e incentivos da Lei do Bem para escalar.",
        "h1": "Contabilidade para " + ORANGE.format("Startups e Tecnologia"),
        "sub": "Estrutura contábil para captar investimento e escalar",
    },
    "empresas-do-fitness": {
        # LOCKED: título, description e textos ficam como estão
        "kind": "sector", "name": "Empresas do Fitness", "parent": SETORES, "service": "Contabilidade para academias e estúdios fitness",
    },
    "politica-de-privacidade": {
        "kind": "legal", "name": "Política de Privacidade",
        "title": "Política de Privacidade | Axxis Contabilidade",
        "description": "Saiba como a Axxis Contabilidade coleta, usa e protege seus dados pessoais, em conformidade com a Lei Geral de Proteção de Dados (LGPD).",
        "sub": "Transparência no tratamento dos seus dados",
        "demote": [(r"<header>\s*<h1>", ".axxis-privacy-policy-content header h1", ".axxis-privacy-policy-content header h2")],
        # o título rebaixado não deve herdar a linha laranja dos H2 de seção
        "css": ".axxis-privacy-policy-content header h2{border-bottom:0;padding-bottom:0}",
    },
    "termos-de-uso": {
        "kind": "legal", "name": "Termos de Uso",
        "title": "Termos de Uso | Axxis Contabilidade",
        "description": "Conheça os termos e condições de uso do site da Axxis Contabilidade Consultiva.",
        "sub": "Regras claras para o uso do nosso site",
    },
}
