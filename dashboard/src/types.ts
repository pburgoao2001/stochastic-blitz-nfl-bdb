export type IC90 = [number, number]

export interface ConIC {
  valor: number
  ic90: IC90
  n: number
}

export interface Contraste {
  estrato: string
  ciega: { exito: number; ic90: IC90; n: number }
  leida: { exito: number; ic90: IC90; n: number }
}

export interface Revelacion {
  mediana_s: number
  ic90: IC90
  prob_disfrazado_2_5s: number
  curva: Array<{ t: number; s: number; lo: number; hi: number }>
  lanzamiento: Array<{ t: number; acumulado: number }>
}

export interface ResumenData {
  titular: string
  n_jugadas: number
  id_liga: ConIC
  efecto: { valor_pp: number; ic90: IC90; n: number; metodo: string }
  contraste: Contraste[]
  revelacion: Revelacion
  validacion: {
    exactitud: number
    auc: number
    brier: number
    exactitud_regla: number
    n: number
    texto: string
  }
  estabilidad?: { r: number | null; spearman_brown: number | null } | null
  sankey: {
    nodes: Array<{ name: string }>
    links: Array<{ source: number; target: number; value: number }>
  }
}

export interface EquipoRow {
  equipo: string
  id: ConIC
  revelacion_mediana_s: number
}

interface EstimacionRival {
  p?: number | null
  ic90?: IC90 | null
  n: number
}

export interface RivalData {
  equipo: string
  filas: Array<{ muestra: string; juega_un_alto: EstimacionRival }>
  formaciones: Array<{ formacion: string; exito: EstimacionRival }>
  validacion_tarjeta?: {
    brier_mezcla?: number | null
    brier_liga?: number | null
    brier_equipo?: number | null
  } | null
  frases: string[]
}

export interface InformeData {
  texto: string
  fuente: 'ia' | 'plantilla'
}

export interface ReplayFrame {
  t: number
  def: Array<[number, number]>
  of: Array<[number, number]>
  balon: [number, number]
  estructura: string
}

export interface ReplayEventos {
  snap: number
  revela: number | null
  lanza: number
}

export interface ReplayData {
  gameId: string | number
  playId: string | number
  descripcion: string
  frames: ReplayFrame[]
  eventos: ReplayEventos
}
