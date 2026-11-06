"""
Simulation de l'univers primordial — formation des structures cosmiques.
===========================================================================

Fichier autonome :  python simulation_universe.py

Physique
--------
Modele N-corps cosmologique de type "Particle-Mesh" (PM), la methode reellement
utilisee en cosmologie numerique (ancetres de Gadget, RAMSES...).

1. On part d'un univers quasi-homogene : des particules de matiere noire posees
   sur une grille reguliere, avec de minuscules fluctuations de densite
   (celles qu'on observe dans le fond diffus cosmologique, ~1e-5).
2. On integre le mouvement en coordonnees COMOBILES : la boite ne grandit pas,
   c'est le facteur d'echelle a(t) qui porte l'expansion. L'equation du
   mouvement en variable x = r/a devient

       dp/dt = -grad(phi) / a          avec p = a^2 dx/dt
       d(phi) : laplacien(phi) = 4 pi G a^2 (rho - rho_moy)

   Seul le CONTRASTE de densite gravite : un univers parfaitement homogene ne
   s'effondre pas, ce qui est le resultat correct.
3. Le potentiel phi est resolu par FFT (equation de Poisson dans l'espace de
   Fourier : phi_k = -4 pi G a^2 delta_k / k^2). C'est O(N log N) sur la grille
   et independant du nombre de particules -> on peut pousser a 100k+ particules.
4. a(t) suit l'equation de Friedmann :

       da/dt = H0 * sqrt(Omega_m/a + Omega_L*a^2 + Omega_k)

Resultat attendu : les fluctuations croissent, la matiere se vide des zones
sous-denses pour tomber dans les sur-densites, et on voit apparaitre le
"reseau cosmique" — murs, filaments, et noeuds ou naissent les galaxies.

Rendu
-----
OpenGL immediat (coherent avec le reste du projet), GL_POINTS en blending
additif, camera orbitale a la souris.

Hadrien Vinay - 2026
"""

import math
import sys

import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# ---------------------------------------------------------------------------
# Constantes d'affichage
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 1280, 800

C_BG = (0.02, 0.02, 0.05)
C_TITLE = (210, 180, 255)
C_TEXT = (200, 200, 215)
C_DIM = (130, 130, 150)
C_ACCENT = (255, 190, 90)
C_PANEL_TOP = (38, 34, 58)
C_PANEL_BOT = (22, 20, 36)
C_BORDER = (110, 100, 160)

# Constantes cosmologiques (unites internes du solveur)
# On travaille en unites ou la boite vaut 1.0 et G = 1 : les valeurs physiques
# ne servent qu'a convertir en Gyr / Mpc pour le HUD.
MPC_PER_KM_S = 977.79222  # 1/(km/s/Mpc) -> Gyr


# ===========================================================================
#  PARAMETRES DE SIMULATION
# ===========================================================================

class SimParams:
    """Jeu de parametres regles depuis le menu."""

    def __init__(self):
        # --- Cosmologie ---
        self.omega_m = 0.31       # densite de matiere
        self.omega_l = 0.69       # energie noire (constante cosmologique)
        self.h0 = 67.7           # constante de Hubble, km/s/Mpc
        # --- Conditions initiales ---
        self.n_side = 48          # N = n_side^3 particules
        self.amplitude = 0.012    # amplitude des fluctuations primordiales
        self.n_spectral = -1.0    # indice du spectre de puissance P(k) ~ k^n
        self.seed = 42
        # --- Expansion ---
        self.expansion = True     # expansion de l'espace active
        self.a_start = 0.02       # facteur d'echelle initial (z = 49)
        # --- Masse negative (modele Janus bimetrique) ---
        self.janus = False        # active la seconde espece, de masse negative
        self.frac_neg = 0.5       # fraction des particules de masse negative
        self.mass_ratio = 1.0     # |m-| / |m+| par particule
        self.omega_neg = 0.0      # contribution de l'espece negative a Friedmann
        # --- Numerique ---
        self.grid = 64            # cellules par axe pour la FFT
        self.box_mpc = 100.0      # taille comobile de la boite, Mpc/h

    @property
    def n_particles(self):
        return self.n_side ** 3

    @property
    def omega_k(self):
        total = self.omega_m + self.omega_l
        if self.janus:
            total -= min(self.omega_neg, 0.95 * self.omega_m)
        return 1.0 - total

    def copy(self):
        p = SimParams()
        p.__dict__.update(self.__dict__)
        return p


PRESETS = {
    "Standard (LCDM)": dict(
        omega_m=0.31, omega_l=0.69, h0=67.7,
        amplitude=0.012, n_spectral=-1.0, expansion=True, a_start=0.02),
    "Sans energie noire": dict(
        omega_m=1.0, omega_l=0.0, h0=67.7,
        amplitude=0.012, n_spectral=-1.0, expansion=True, a_start=0.02),
    "Univers froid et dense": dict(
        omega_m=2.5, omega_l=0.0, h0=50.0,
        amplitude=0.02, n_spectral=-1.0, expansion=True, a_start=0.05),
    "Fluctuations fortes": dict(
        omega_m=0.31, omega_l=0.69, h0=67.7,
        amplitude=0.06, n_spectral=-1.5, expansion=True, a_start=0.02),
    "Sans expansion": dict(
        omega_m=1.0, omega_l=0.0, h0=67.7,
        amplitude=0.02, n_spectral=-1.0, expansion=False, a_start=1.0),
    "Janus (masse negative)": dict(
        # Pas d'energie noire : dans Janus c'est la repulsion de l'espece
        # negative qui joue ce role et dilate les vides.
        # Omega_neg < Omega_m, sinon la densite d'energie totale devient
        # negative et l'expansion n'a plus de solution.
        omega_m=1.0, omega_l=0.0, h0=67.7,
        amplitude=0.012, n_spectral=-1.0, expansion=True, a_start=0.02,
        janus=True, frac_neg=0.5, mass_ratio=1.0, omega_neg=0.55),
}


# ===========================================================================
#  MOTEUR : PARTICLE-MESH + FFT
# ===========================================================================

class UniverseSim:
    """Simulation N-corps cosmologique en coordonnees comobiles."""

    def __init__(self, params):
        self.p = params
        self.ng = int(params.grid)
        self.box = 1.0                      # boite unite [0,1)^3, periodique
        self.a = params.a_start if params.expansion else 1.0
        self.t = 0.0                        # temps super-conforme interne
        self.t_cosmic = 0.0                 # temps propre, en unites de 1/H0
        self.step_count = 0

        self._init_particles()
        self._init_poisson_kernel()
        self._density = np.zeros((self.ng,) * 3, dtype=np.float64)
        self.acc = np.zeros_like(self.pos)
        self.local_density = np.zeros(len(self.pos), dtype=np.float32)
        self.density_pos = np.zeros(len(self.pos), dtype=np.float32)
        self.density_neg = np.zeros(len(self.pos), dtype=np.float32)
        self._compute_forces()

    # -- conditions initiales ------------------------------------------------

    def _init_particles(self):
        """Grille reguliere + deplacement de Zel'dovich (approximation lineaire).

        Plutot que de bruiter les positions au hasard, on genere un champ de
        fluctuations gaussien de spectre P(k) ~ k^n, on en deduit le potentiel
        de vitesse, et on deplace chaque particule de -grad(psi). C'est
        l'approximation de Zel'dovich : elle donne d'emblee des positions ET
        des vitesses coherentes, donc les filaments apparaissent vite au lieu
        d'etre noyes dans du bruit blanc.
        """
        p = self.p
        n = int(p.n_side)
        rng = np.random.default_rng(int(p.seed))

        # Grille de depart (positions "lagrangiennes") en [0,1)
        lin = (np.arange(n) + 0.5) / n
        gx, gy, gz = np.meshgrid(lin, lin, lin, indexing="ij")
        q = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)

        # Champ gaussien aleatoire sur la grille de particules
        ng = n
        white = rng.standard_normal((ng, ng, ng))
        wk = np.fft.rfftn(white)

        kx = 2.0 * np.pi * np.fft.fftfreq(ng)
        kz = 2.0 * np.pi * np.fft.rfftfreq(ng)
        KX = kx[:, None, None]
        KY = kx[None, :, None]
        KZ = kz[None, None, :]
        k2 = KX ** 2 + KY ** 2 + KZ ** 2
        k2[0, 0, 0] = 1.0

        # Spectre de puissance : amplitude ~ k^(n/2), n = indice spectral
        kmag = np.sqrt(k2)
        power = kmag ** (p.n_spectral / 2.0)
        power[0, 0, 0] = 0.0
        delta_k = wk * power

        # Potentiel de vitesse : psi_k = -delta_k / k^2
        psi_k = -delta_k / k2
        psi_k[0, 0, 0] = 0.0

        # Deplacement = -grad(psi)  ->  dans Fourier : -i*k*psi_k
        disp = np.empty((len(q), 3))
        for axis, K in enumerate((KX, KY, KZ)):
            field = np.fft.irfftn(-1j * K * psi_k, s=(ng, ng, ng))
            disp[:, axis] = field.ravel()

        # Normalisation sur l'amplitude demandee (rms du deplacement)
        rms = np.sqrt(np.mean(np.sum(disp ** 2, axis=1)))
        if rms > 0:
            disp *= p.amplitude / rms

        self.pos = np.mod(q + disp, 1.0)

        # Vitesses de Zel'dovich : proportionnelles au deplacement.
        # En variable p = a^2 dx/dt, la croissance lineaire donne v ~ disp.
        if p.expansion:
            self.vel = disp * self._growth_rate_factor()
        else:
            self.vel = np.zeros_like(disp)

        self.pos = np.ascontiguousarray(self.pos, dtype=np.float64)
        self.vel = np.ascontiguousarray(self.vel, dtype=np.float64)

        # --- Especes (modele Janus) ------------------------------------
        # is_neg : masque des particules de masse negative.
        # mass   : masse signee, en unites de la masse d'une particule (+).
        n_tot = len(self.pos)
        if p.janus and p.frac_neg > 0.0:
            n_neg = int(round(n_tot * min(max(p.frac_neg, 0.0), 0.95)))
            idx = rng.permutation(n_tot)[:n_neg]
            self.is_neg = np.zeros(n_tot, dtype=bool)
            self.is_neg[idx] = True
        else:
            self.is_neg = np.zeros(n_tot, dtype=bool)

        self.mass = np.ones(n_tot, dtype=np.float64)
        self.mass[self.is_neg] = -abs(p.mass_ratio)
        self.idx_pos = np.flatnonzero(~self.is_neg)
        self.idx_neg = np.flatnonzero(self.is_neg)

    def _growth_rate_factor(self):
        """Facteur de conversion deplacement -> impulsion comobile initiale."""
        a = self.a
        return a * self._hubble(a) * a  # a^2 * H : coherent avec p = a^2 dx/dt

    # -- solveur de Poisson --------------------------------------------------

    def _init_poisson_kernel(self):
        """Precalcule 1/k^2 (noyau de Green) et les vecteurs k pour la FFT."""
        ng = self.ng
        kx = 2.0 * np.pi * np.fft.fftfreq(ng, d=1.0 / ng)
        kz = 2.0 * np.pi * np.fft.rfftfreq(ng, d=1.0 / ng)
        self.KX = kx[:, None, None]
        self.KY = kx[None, :, None]
        self.KZ = kz[None, None, :]
        k2 = self.KX ** 2 + self.KY ** 2 + self.KZ ** 2
        k2[0, 0, 0] = 1.0            # evite la division par zero
        self.inv_k2 = 1.0 / k2
        self.inv_k2[0, 0, 0] = 0.0   # on retire le mode moyen (univers homogene)

    def _cic_weights(self, sel=None):
        """Indices et poids CIC pour les particules selectionnees.

        Mutualise entre le depot de masse et l'interpolation des forces :
        c'est le MEME noyau des deux cotes, ce qui garantit l'absence
        d'auto-force.
        """
        ng = self.ng
        pos = self.pos if sel is None else self.pos[sel]
        g = pos * ng
        i0 = np.floor(g).astype(np.int64)
        f = g - i0
        i0 %= ng
        i1 = (i0 + 1) % ng
        ix = (i0[:, 0], i1[:, 0])
        iy = (i0[:, 1], i1[:, 1])
        iz = (i0[:, 2], i1[:, 2])
        wxs = (1.0 - f[:, 0], f[:, 0])
        wys = (1.0 - f[:, 1], f[:, 1])
        wzs = (1.0 - f[:, 2], f[:, 2])
        return ix, iy, iz, wxs, wys, wzs

    def _deposit_mass(self, sel=None, weight=None, out=None):
        """Depose les particules sur la grille — CIC (Cloud In Cell).

        Chaque particule repartit sa masse sur les 8 cellules voisines avec un
        poids trilineaire. C'est ce qui rend le champ de force lisse et evite
        le bruit de grille.

        sel    : indices des particules a deposer (toutes si None)
        weight : poids par particule (1.0 si None)
        """
        ng = self.ng
        ix, iy, iz, wxs, wys, wzs = self._cic_weights(sel)

        rho = self._density if out is None else out
        rho.fill(0.0)
        flat = rho.ravel()

        for a_ in range(2):
            for b_ in range(2):
                base = (ix[a_] * ng + iy[b_]) * ng
                wab = wxs[a_] * wys[b_]
                if weight is not None:
                    wab = wab * weight
                for c_ in range(2):
                    np.add.at(flat, base + iz[c_], wab * wzs[c_])
        return rho

    def _solve_potential_acc(self, delta, coupling):
        """Resout Poisson pour un contraste donne et renvoie l'acceleration.

        coupling : facteur 1.5 * Omega * a^2, qui porte l'intensite ET le
        signe de la source.
        """
        ng = self.ng
        delta_k = np.fft.rfftn(delta)
        phi_k = -coupling * delta_k * self.inv_k2
        return [np.fft.irfftn(-1j * K * phi_k, s=(ng, ng, ng))
                for K in (self.KX, self.KY, self.KZ)]

    def _gather(self, field_flat, ix, iy, iz, wxs, wys, wzs, n):
        """Interpolation CIC inverse grille -> particules."""
        ng = self.ng
        out = np.zeros(n)
        for a_ in range(2):
            for b_ in range(2):
                base = (ix[a_] * ng + iy[b_]) * ng
                wab = wxs[a_] * wys[b_]
                for c_ in range(2):
                    out += field_flat[base + iz[c_]] * wab * wzs[c_]
        return out

    def _compute_forces(self):
        """Resout Poisson par FFT et interpole l'acceleration aux particules.

        Modele standard (janus = False) : un seul potentiel, tout le monde
        s'attire.

        Modele JANUS bimetrique (janus = True) : deux especes, deux sources.
        L'acceleration d'une particule depend de son espece :

            a(+) = -grad(phi+)  +  grad(phi-)     attiree par (+), repoussee par (-)
            a(-) = -grad(phi-)  +  grad(phi+)     attiree par (-), repoussee par (+)

        Autrement dit les masses de MEME signe s'attirent, celles de signes
        OPPOSES se repoussent. C'est ce qui distingue Janus du modele naif de
        Bondi (une seule metrique), ou une paire (+,-) s'auto-accelere
        indefiniment — la fameuse "course en couple", non physique.
        """
        ng = self.ng
        n_part = len(self.pos)
        p = self.p
        a_fac = (self.a ** 2) if p.expansion else 1.0

        ix, iy, iz, wxs, wys, wzs = self._cic_weights()

        if not p.janus or len(self.idx_neg) == 0:
            rho = self._deposit_mass()
            mean = n_part / float(ng ** 3)
            delta = rho / mean - 1.0
            acc_grid = self._solve_potential_acc(
                delta, 1.5 * p.omega_m * a_fac)
            for axis in range(3):
                self.acc[:, axis] = self._gather(
                    acc_grid[axis].ravel(), ix, iy, iz, wxs, wys, wzs, n_part)
            self.local_density = self._gather(
                (rho / mean).ravel(), ix, iy, iz,
                wxs, wys, wzs, n_part).astype(np.float32)
            self.density_pos = self.local_density
            self.density_neg = np.zeros(n_part, dtype=np.float32)
            return

        # --- Janus : deux grilles de densite, deux potentiels --------------
        n_pos = len(self.idx_pos)
        n_neg = len(self.idx_neg)
        cell = float(ng ** 3)

        rho_p = self._deposit_mass(sel=self.idx_pos,
                                   out=np.zeros((ng,) * 3))
        # L'espece negative est ponderee par |m-|/|m+| : une particule
        # negative peut etre plus legere qu'une positive.
        w_neg = abs(p.mass_ratio)
        rho_n = self._deposit_mass(sel=self.idx_neg,
                                   weight=np.full(n_neg, w_neg),
                                   out=np.zeros((ng,) * 3))

        # Chaque espece est comparee a SA propre moyenne : une distribution
        # uniforme ne doit produire aucune force, pour l'une comme pour l'autre.
        mean_p = max(n_pos / cell, 1e-12)
        mean_n = max(n_neg * w_neg / cell, 1e-12)
        delta_p = rho_p / mean_p - 1.0
        delta_n = rho_n / mean_n - 1.0

        # Intensite de chaque source.
        #
        # Attention : le contraste delta est invariant par changement d'echelle
        # de masse (rho et sa moyenne portent le meme facteur, qui se
        # simplifie). Le rapport des masses et l'abondance relative doivent
        # donc agir ICI, sur l'amplitude du potentiel, et non sur le depot.
        #
        # Poids physique d'une espece = (nombre de particules) x (masse unitaire).
        tot_p = max(n_pos, 1e-12)
        tot_n = n_neg * w_neg
        om_p = p.omega_m
        om_n = p.omega_neg if p.omega_neg > 0.0 else p.omega_m
        # On module par la part reelle de chaque espece dans la masse totale,
        # normalisee pour qu'a 50/50 et mass_ratio = 1 on retrouve om_p et om_n.
        tot = tot_p + tot_n
        om_p *= 2.0 * tot_p / tot
        om_n *= 2.0 * tot_n / tot
        acc_p = self._solve_potential_acc(delta_p, 1.5 * om_p * a_fac)
        acc_n = self._solve_potential_acc(delta_n, 1.5 * om_n * a_fac)

        sign = np.where(self.is_neg, -1.0, 1.0)
        for axis in range(3):
            g_p = self._gather(acc_p[axis].ravel(), ix, iy, iz,
                               wxs, wys, wzs, n_part)
            g_n = self._gather(acc_n[axis].ravel(), ix, iy, iz,
                               wxs, wys, wzs, n_part)
            # (+) : +g_p - g_n     (-) : -g_p + g_n   -> facteur sign
            self.acc[:, axis] = sign * (g_p - g_n)

        self.density_pos = self._gather((rho_p / mean_p).ravel(), ix, iy, iz,
                                        wxs, wys, wzs, n_part).astype(np.float32)
        self.density_neg = self._gather((rho_n / mean_n).ravel(), ix, iy, iz,
                                        wxs, wys, wzs, n_part).astype(np.float32)
        # Pour la coloration : chaque particule voit la densite de son espece.
        self.local_density = np.where(self.is_neg,
                                      self.density_neg,
                                      self.density_pos).astype(np.float32)

    # -- cosmologie ----------------------------------------------------------

    def _hubble(self, a):
        """H(a)/H0 : equation de Friedmann.

            H(a)^2 / H0^2 = Omega_m/a^3 + Omega_L + Omega_k/a^2
        """
        p = self.p
        a = max(a, 1e-8)
        val = p.omega_m / (a ** 3) + p.omega_l + p.omega_k / (a * a)
        if p.janus:
            # L'espece negative contribue negativement a la densite d'energie :
            # elle accelere l'expansion, comme le fait une constante
            # cosmologique dans le modele standard. C'est l'argument central
            # de Janus pour se passer d'energie noire.
            #
            # On borne la contribution a Omega_m : au-dela, la densite
            # d'energie totale deviendrait negative et H(a) n'aurait plus de
            # solution reelle — l'expansion se figerait au lieu d'accelerer.
            val -= min(p.omega_neg, 0.95 * p.omega_m) / (a ** 3)
        return math.sqrt(max(val, 1e-12))

    def _da_dt(self, a):
        """da/dt en unites internes (H0 = 1)."""
        return a * self._hubble(a)

    # -- integration ---------------------------------------------------------

    def step(self, dt):
        """Un pas de kick-drift-kick (leapfrog), stable et symplectique."""
        expanding = self.p.expansion

        # Kick 1/2
        if expanding:
            self.vel += self.acc * (0.5 * dt / self.a)
        else:
            self.vel += self.acc * (0.5 * dt)

        # Drift : dx/dt = p / a^2  en comobile
        if expanding:
            # a avance en Runge-Kutta 2 sur le demi-pas pour la precision
            a_half = self.a + 0.5 * dt * self._da_dt(self.a)
            self.pos += self.vel * (dt / (a_half ** 2))
            self.a += dt * self._da_dt(a_half)
            # a est avance par da = dt * (da/dt), donc dt est bien un pas de
            # temps PROPRE (cosmique). Le drift, lui, divise par a^2 car la
            # variable conjuguee est p = a^2 dx/dt.
            self.t_cosmic += dt
        else:
            self.pos += self.vel * dt
            self.t_cosmic += dt

        np.mod(self.pos, 1.0, out=self.pos)   # boite periodique

        # Forces au nouveau point
        self._compute_forces()

        # Kick 1/2
        if expanding:
            self.vel += self.acc * (0.5 * dt / self.a)
        else:
            self.vel += self.acc * (0.5 * dt)

        self.t += dt
        self.step_count += 1

    # -- diagnostics ---------------------------------------------------------

    @property
    def redshift(self):
        if not self.p.expansion:
            return 0.0
        return max(1.0 / max(self.a, 1e-8) - 1.0, 0.0)

    @property
    def age_gyr(self):
        """Temps propre ecoule depuis le debut, en milliards d'annees.

        Le temps interne est en unites de 1/H0 ; 1/H0 vaut 977.79/h0 Gyr
        quand h0 est exprime en km/s/Mpc (temps de Hubble).
        """
        hubble_time_gyr = MPC_PER_KM_S / max(self.p.h0, 1e-6)
        return self.t_cosmic * hubble_time_gyr

    def speeds(self):
        return np.linalg.norm(self.vel, axis=1)

    def clump_fraction(self, threshold=5.0):
        """Fraction de la matiere dans des zones sur-denses (proto-galaxies)."""
        return float(np.mean(self.local_density > threshold))


# ===========================================================================
#  WIDGETS (menu)
# ===========================================================================

def _blit_gl(surf, x, y):
    """Affiche une surface pygame en overlay 2D."""
    data = pygame.image.tobytes(surf, "RGBA", True)
    glRasterPos2f(x, y)
    glDrawPixels(surf.get_width(), surf.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, data)


def draw_text(font, text, color, x, y):
    _blit_gl(font.render(text, True, color), x, y)


def draw_rect(x, y, w, h, color, alpha=1.0):
    glColor4f(color[0] / 255.0, color[1] / 255.0, color[2] / 255.0, alpha)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x, y + h)
    glEnd()


def draw_gradient(x, y, w, h, top, bot):
    glBegin(GL_QUADS)
    glColor3f(bot[0] / 255.0, bot[1] / 255.0, bot[2] / 255.0)
    glVertex2f(x, y)
    glVertex2f(x + w, y)
    glColor3f(top[0] / 255.0, top[1] / 255.0, top[2] / 255.0)
    glVertex2f(x + w, y + h)
    glVertex2f(x, y + h)
    glEnd()


def draw_border(x, y, w, h, color=C_BORDER, width=1.0):
    glLineWidth(width)
    glColor3f(color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x, y + h)
    glEnd()
    glLineWidth(1.0)


class Slider:
    """Slider horizontal cliquable et glissable.

    Les coordonnees sont en repere OpenGL 2D (origine en bas a gauche).
    """

    H = 8
    KNOB = 7

    def __init__(self, x, y, w, label, vmin, vmax, attr, fmt="%.3f",
                 step=None, integer=False, unit=""):
        self.x, self.y, self.w = x, y, w
        self.label = label
        self.vmin, self.vmax = vmin, vmax
        self.attr = attr
        self.fmt = fmt
        self.step = step
        self.integer = integer
        self.unit = unit
        self.dragging = False

    def value(self, params):
        return getattr(params, self.attr)

    def _frac(self, params):
        v = self.value(params)
        return (v - self.vmin) / (self.vmax - self.vmin)

    def hit(self, mx, my):
        return (self.x - self.KNOB <= mx <= self.x + self.w + self.KNOB and
                self.y - 12 <= my <= self.y + self.H + 12)

    def set_from_mouse(self, mx, params):
        frac = min(max((mx - self.x) / float(self.w), 0.0), 1.0)
        v = self.vmin + frac * (self.vmax - self.vmin)
        if self.step:
            v = round(v / self.step) * self.step
        if self.integer:
            v = int(round(v))
        setattr(params, self.attr, v)

    def draw(self, params, font, font_small):
        frac = self._frac(params)
        # rail
        draw_rect(self.x, self.y, self.w, self.H, (55, 52, 78))
        # remplissage
        draw_rect(self.x, self.y, self.w * frac, self.H, (120, 100, 200))
        draw_border(self.x, self.y, self.w, self.H, (90, 85, 125))
        # curseur
        kx = self.x + self.w * frac
        col = C_ACCENT if self.dragging else (235, 230, 255)
        draw_rect(kx - 4, self.y - 5, 8, self.H + 10, col)
        # libelles
        draw_text(font_small, self.label, C_TEXT, self.x, self.y + self.H + 6)
        val = self.fmt % self.value(params)
        draw_text(font_small, val + self.unit, C_ACCENT,
                  self.x + self.w - 70, self.y + self.H + 6)


class TextButton:
    def __init__(self, x, y, w, h, text, small=False):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.text = text
        self.small = small
        self.active = False

    def hit(self, mx, my):
        return self.x <= mx <= self.x + self.w and self.y <= my <= self.y + self.h

    def draw(self, font, mx=-1, my=-1):
        hov = self.hit(mx, my)
        if self.active:
            top, bot = (95, 80, 160), (60, 50, 110)
        elif hov:
            top, bot = (62, 56, 92), (40, 36, 62)
        else:
            top, bot = C_PANEL_TOP, C_PANEL_BOT
        draw_gradient(self.x, self.y, self.w, self.h, top, bot)
        draw_border(self.x, self.y, self.w, self.h,
                    C_ACCENT if (hov or self.active) else C_BORDER)
        col = (255, 255, 255) if (hov or self.active) else C_TEXT
        # Tronque si le libelle depasse la largeur du bouton.
        label = self.text
        while label and font.size(label)[0] > self.w - 12:
            label = label[:-1]
        if label != self.text and len(label) > 1:
            label = label[:-1] + "."
        surf = font.render(label, True, col)
        draw_text(font, label, col,
                  self.x + (self.w - surf.get_width()) // 2,
                  self.y + (self.h - surf.get_height()) // 2 + 2)


# ===========================================================================
#  CAMERA
# ===========================================================================

class OrbitCamera:
    def __init__(self):
        self.yaw = 35.0
        self.pitch = 22.0
        self.dist = 2.4

    def apply(self):
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -self.dist)
        glRotatef(self.pitch, 1.0, 0.0, 0.0)
        glRotatef(self.yaw, 0.0, 1.0, 0.0)
        glTranslatef(-0.5, -0.5, -0.5)   # boite centree sur [0,1]^3

    def zoom(self, delta):
        self.dist = min(max(self.dist * (1.0 - 0.12 * delta), 0.25), 8.0)


# ===========================================================================
#  COLORATION DES PARTICULES
# ===========================================================================

COLOR_MODES = ["Densite locale", "Vitesse", "Amas / halos", "Especes (Janus)"]


def build_colors(sim, mode):
    """Retourne un tableau (N,4) float32 RGBA pour le rendu additif.

    Le canal alpha est essentiel : en blending additif, des dizaines de
    milliers de points se superposent et saturent en blanc si chacun est
    opaque. On rend donc la matiere diffuse presque transparente et on
    reserve l'opacite aux sur-densites — c'est ce qui fait ressortir les
    filaments et les noeuds du reseau cosmique.
    """
    n = len(sim.pos)
    out = np.empty((n, 4), dtype=np.float32)

    # Contraste de densite normalise en echelle log, commun a plusieurs modes.
    d = np.clip(sim.local_density, 0.02, None)
    # t = 0 pour le vide, 0.5 autour de la densite moyenne, 1 dans les amas.
    t = np.clip((np.log10(d) + 1.0) / 3.0, 0.0, 1.0)

    if mode == 0:  # densite : bleu nuit -> cyan -> or -> blanc
        # La rampe est etalee sur la plage de t reellement occupee (~0.3-0.8),
        # sinon tout reste bleu et les amas ne virent jamais a l'or.
        u = np.clip((t - 0.30) / 0.45, 0.0, 1.0)
        out[:, 0] = np.clip(0.15 + 1.70 * np.clip(u - 0.30, 0, 1), 0, 1)
        out[:, 1] = np.clip(0.35 + 1.30 * np.clip(u - 0.15, 0, 1), 0, 1)
        out[:, 2] = np.clip(0.80 + 0.5 * u - 1.9 * np.clip(u - 0.55, 0, 1), 0, 1)
        out[:, 3] = 0.10 + 0.90 * (u ** 2)

    elif mode == 1:  # vitesse : bleu froid -> magenta -> orange chaud
        s = sim.speeds()
        hi = np.percentile(s, 98) if n else 1.0
        v = np.clip(s / max(hi, 1e-12), 0.0, 1.0)
        out[:, 0] = np.clip(0.15 + 1.5 * v, 0, 1)
        out[:, 1] = np.clip(0.10 + 1.1 * v * v, 0, 1)
        out[:, 2] = np.clip(0.95 - 1.0 * v, 0, 1)
        out[:, 3] = 0.06 + 0.80 * (0.35 * v + 0.65 * t ** 2)

    elif mode == 3:  # especes : matiere positive doree, negative bleu froid
        pos_hot = np.clip((t - 0.30) / 0.45, 0.0, 1.0)
        neg = sim.is_neg
        # (+) : or -> blanc    (-) : cyan -> violet
        out[:, 0] = np.where(neg, 0.25 + 0.35 * pos_hot, 1.0)
        out[:, 1] = np.where(neg, 0.45 + 0.25 * pos_hot, 0.72 + 0.28 * pos_hot)
        out[:, 2] = np.where(neg, 1.0, 0.25 + 0.60 * pos_hot)
        out[:, 3] = 0.08 + 0.80 * (pos_hot ** 2)

    else:  # amas : champ diffus efface, halos en rouge -> blanc incandescent
        in_halo = sim.local_density > 5.0
        h = np.clip((np.log10(d) - 0.7) / 1.5, 0.0, 1.0)
        out[:, 0] = np.where(in_halo, 1.0, 0.18)
        out[:, 1] = np.where(in_halo, 0.25 + 0.75 * h, 0.20)
        out[:, 2] = np.where(in_halo, 0.10 + 0.90 * h * h, 0.30)
        out[:, 3] = np.where(in_halo, 0.25 + 0.75 * h, 0.025)

    # En mode Janus, la masse negative garde une teinte froide dans tous les
    # modes (sauf le mode Especes, qui gere deja les deux palettes) : sans
    # cela on ne distingue plus les especes quand on isole l'une des deux.
    if mode != 3 and getattr(sim, "is_neg", None) is not None and sim.is_neg.any():
        neg = sim.is_neg
        r, g_, b = out[neg, 0].copy(), out[neg, 1].copy(), out[neg, 2].copy()
        lum = 0.30 * r + 0.59 * g_ + 0.11 * b
        out[neg, 0] = 0.20 * lum
        out[neg, 1] = 0.55 * lum + 0.10
        out[neg, 2] = 0.60 + 0.40 * lum

    return out


# ===========================================================================
#  ECRAN DE MENU
# ===========================================================================

def build_menu_widgets():
    """Construit presets, sliders et boutons. Coords OpenGL (y vers le haut)."""
    sliders = []
    col_x = 90
    col2_x = 700
    w = 420

    # Colonne 1 — Cosmologie
    y = HEIGHT - 240
    sliders.append(Slider(col_x, y, w, "Omega matiere  (densite de matiere)",
                          0.05, 2.5, "omega_m", "%.2f"))
    y -= 62
    sliders.append(Slider(col_x, y, w, "Omega Lambda  (energie noire)",
                          0.0, 1.5, "omega_l", "%.2f"))
    y -= 62
    sliders.append(Slider(col_x, y, w, "H0  constante de Hubble",
                          40.0, 100.0, "h0", "%.1f", unit=" km/s/Mpc"))
    y -= 62
    sliders.append(Slider(col_x, y, w, "Taille de la boite comobile",
                          20.0, 400.0, "box_mpc", "%.0f", step=5.0, unit=" Mpc"))

    # Colonne 2 — Conditions initiales / expansion
    y = HEIGHT - 240
    sliders.append(Slider(col2_x, y, w, "N par axe  (particules = N^3)",
                          16, 80, "n_side", "%d", step=4, integer=True))
    y -= 62
    sliders.append(Slider(col2_x, y, w, "Amplitude des fluctuations primordiales",
                          0.001, 0.08, "amplitude", "%.4f"))
    y -= 62
    sliders.append(Slider(col2_x, y, w, "Indice spectral n  (P(k) ~ k^n)",
                          -2.5, 1.0, "n_spectral", "%.2f"))
    y -= 62
    sliders.append(Slider(col2_x, y, w, "Facteur d'echelle initial a",
                          0.01, 1.0, "a_start", "%.3f"))

    # Colonne 1 (suite) — Masse negative / Janus.
    # Ces sliders ne sont dessines que si le mode Janus est actif.
    y_janus = HEIGHT - 240 - 4 * 62 - 34
    janus_sliders = []
    janus_sliders.append(Slider(col_x, y_janus, w,
                                "Fraction de masse negative",
                                0.0, 0.9, "frac_neg", "%.2f"))
    y_janus -= 62
    janus_sliders.append(Slider(col_x, y_janus, w,
                                "Rapport des masses  |m-| / |m+|",
                                0.1, 3.0, "mass_ratio", "%.2f"))
    y_janus -= 62
    janus_sliders.append(Slider(col_x, y_janus, w,
                                "Omega negatif  (poids gravitationnel)",
                                0.0, 2.0, "omega_neg", "%.2f"))
    sliders.extend(janus_sliders)

    # Presets repartis sur toute la largeur utile (de x=90 au bord droit),
    # pour que le dernier bouton ne deborde pas quel que soit leur nombre.
    presets = []
    n_preset = len(PRESETS)
    gap = 12
    avail = (WIDTH - 90) - 90                       # marges gauche et droite
    bw = int((avail - gap * (n_preset - 1)) / n_preset)
    for i, name in enumerate(PRESETS):
        presets.append(TextButton(90 + i * (bw + gap), HEIGHT - 150, bw, 42,
                                  name, small=True))

    toggle = TextButton(col2_x, HEIGHT - 240 - 4 * 62 - 10, 200, 38,
                        "Expansion : ON")
    seed_btn = TextButton(col2_x + 220, HEIGHT - 240 - 4 * 62 - 10, 200, 38,
                          "Graine : 42")
    janus_btn = TextButton(col_x, HEIGHT - 240 - 4 * 62 + 16, 420, 38,
                           "Masse negative (Janus) : OFF")
    start = TextButton(WIDTH // 2 - 160, 70, 320, 56, "LANCER LE BIG BANG")
    quit_btn = TextButton(WIDTH - 150, 20, 120, 34, "Quitter", small=True)

    return (sliders, presets, toggle, seed_btn, start, quit_btn,
            janus_btn, janus_sliders)


def menu_screen(params, fonts, clock):
    """Boucle du menu. Retourne True pour lancer, False pour quitter."""
    f_title, f_sub, f_btn, f_small = fonts
    (sliders, presets, toggle, seed_btn, start, quit_btn,
     janus_btn, janus_sliders) = build_menu_widgets()
    janus_set = set(id(s) for s in janus_sliders)

    def slider_visible(s):
        """Un slider masque ne doit etre ni dessine ni cliquable."""
        if id(s) in janus_set and not params.janus:
            return False
        if s.attr == "a_start" and not params.expansion:
            return False
        return True

    rng = np.random.default_rng()

    while True:
        mx_raw, my_raw = pygame.mouse.get_pos()
        mx, my = mx_raw, HEIGHT - my_raw   # repere OpenGL

        for ev in pygame.event.get():
            if ev.type == QUIT:
                return False
            if ev.type == KEYDOWN:
                if ev.key == K_ESCAPE:
                    return False
                if ev.key in (K_RETURN, K_KP_ENTER):
                    return True
            if ev.type == MOUSEBUTTONDOWN and ev.button == 1:
                if start.hit(mx, my):
                    return True
                if quit_btn.hit(mx, my):
                    return False
                if janus_btn.hit(mx, my):
                    params.janus = not params.janus
                if toggle.hit(mx, my):
                    params.expansion = not params.expansion
                    if not params.expansion:
                        params.a_start = 1.0
                if seed_btn.hit(mx, my):
                    params.seed = int(rng.integers(0, 10000))
                for i, b in enumerate(presets):
                    if b.hit(mx, my):
                        name = list(PRESETS)[i]
                        # Un preset qui ne parle pas de Janus desactive la
                        # masse negative, sinon elle resterait active d'un
                        # scenario a l'autre sans que ce soit visible.
                        if "janus" not in PRESETS[name]:
                            params.janus = False
                        for k, v in PRESETS[name].items():
                            setattr(params, k, v)
                        for bb in presets:
                            bb.active = False
                        b.active = True
                for s in sliders:
                    if slider_visible(s) and s.hit(mx, my):
                        s.dragging = True
                        s.set_from_mouse(mx, params)
            if ev.type == MOUSEBUTTONUP and ev.button == 1:
                for s in sliders:
                    s.dragging = False
            if ev.type == MOUSEMOTION:
                for s in sliders:
                    if s.dragging:
                        s.set_from_mouse(mx, params)
            if ev.type == MOUSEWHEEL:
                pass

        # cohérence : a_start est fige a 1 sans expansion
        if not params.expansion:
            params.a_start = 1.0
        toggle.text = "Expansion : " + ("ON" if params.expansion else "OFF")
        seed_btn.text = "Graine : %d" % params.seed

        # ---- rendu ----
        glClearColor(*C_BG, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, WIDTH, 0, HEIGHT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        draw_gradient(0, 0, WIDTH, HEIGHT, (14, 12, 26), (4, 4, 10))

        draw_text(f_title, "UNIVERS PRIMORDIAL  —  FORMATION DES STRUCTURES",
                  C_TITLE, 90, HEIGHT - 70)
        draw_text(f_sub, "Simulation N-corps cosmologique (Particle-Mesh / FFT)"
                  "  —  reglez les parametres puis lancez",
                  C_DIM, 90, HEIGHT - 100)

        draw_text(f_small, "SCENARIOS", C_ACCENT, 90, HEIGHT - 128)
        for b in presets:
            b.draw(f_small, mx, my)

        draw_text(f_small, "COSMOLOGIE", C_ACCENT, 90, HEIGHT - 212)
        draw_text(f_small, "CONDITIONS INITIALES & EXPANSION", C_ACCENT,
                  700, HEIGHT - 212)

        for s in sliders:
            if not slider_visible(s):
                continue
            s.draw(params, f_btn, f_small)

        janus_btn.text = ("Masse negative (Janus) : "
                          + ("ON" if params.janus else "OFF"))
        janus_btn.active = params.janus
        janus_btn.draw(f_small, mx, my)
        toggle.draw(f_small, mx, my)
        seed_btn.draw(f_small, mx, my)

        # Panneau récapitulatif
        n = params.n_particles
        omk = params.omega_k
        info_y = 190
        draw_gradient(90, info_y - 10, WIDTH - 270, 92, (26, 24, 42), (16, 15, 28))
        draw_border(90, info_y - 10, WIDTH - 270, 92)
        draw_text(f_small, "Particules : %s   |   Grille FFT : %d^3   |   "
                  "Redshift initial z = %.1f" % (f"{n:,}".replace(",", " "),
                                                 params.grid,
                                                 1.0 / max(params.a_start, 1e-6) - 1.0),
                  C_TEXT, 110, info_y + 52)
        if params.janus and params.omega_neg > params.omega_m:
            draw_text(f_small, "Omega negatif est plafonne a Omega matiere : "
                      "au-dela l'expansion n'a plus de solution reelle.",
                      (255, 190, 120), 110, info_y + 70)
        geom = ("plat" if abs(omk) < 0.02 else
                ("ouvert" if omk > 0 else "ferme"))
        draw_text(f_small, "Omega total = %.2f  ->  univers %s   |   "
                  "Omega courbure = %+.2f" % (params.omega_m + params.omega_l,
                                              geom, omk),
                  C_DIM, 110, info_y + 28)
        if n > 250000:
            draw_text(f_small, "Attention : au-dela de ~250 000 particules la "
                      "simulation tourne au ralenti (~15 pas/s).",
                      (255, 150, 120), 110, info_y + 4)
        else:
            draw_text(f_small, "Astuce : 'Sans energie noire' s'effondre bien plus "
                      "que LCDM — comparez les deux.", C_DIM, 110, info_y + 4)

        start.draw(f_btn, mx, my)
        quit_btn.draw(f_small, mx, my)

        pygame.display.flip()
        clock.tick(60)


# ===========================================================================
#  ECRAN DE SIMULATION
# ===========================================================================

def draw_box_wireframe():
    glColor4f(0.30, 0.28, 0.45, 0.55)
    glBegin(GL_LINES)
    edges = [
        (0, 0, 0, 1, 0, 0), (0, 0, 0, 0, 1, 0), (0, 0, 0, 0, 0, 1),
        (1, 1, 1, 0, 1, 1), (1, 1, 1, 1, 0, 1), (1, 1, 1, 1, 1, 0),
        (1, 0, 0, 1, 1, 0), (1, 0, 0, 1, 0, 1), (0, 1, 0, 1, 1, 0),
        (0, 1, 0, 0, 1, 1), (0, 0, 1, 1, 0, 1), (0, 0, 1, 0, 1, 1),
    ]
    for x0, y0, z0, x1, y1, z1 in edges:
        glVertex3f(x0, y0, z0)
        glVertex3f(x1, y1, z1)
    glEnd()


def simulate_screen(params, fonts, clock):
    """Boucle de simulation. Retourne 'menu' ou 'quit'."""
    f_title, f_sub, f_btn, f_small = fonts

    sim = UniverseSim(params)
    cam = OrbitCamera()
    colors = build_colors(sim, 0)

    color_mode = 0
    paused = False
    # dt est un pas de temps propre en unites de 1/H0 (~14.5 Gyr).
    # 0.0006 -> ~1600 pas pour aller de a=0.02 a a=1, soit environ 30 s
    # a 60 fps : assez lent pour voir les filaments se former.
    steps_per_frame = 1
    dt = 0.0006
    point_size = 1.8
    show_box = True
    # 0 = les deux especes, 1 = matiere positive seule, 2 = negative seule
    species_view = 0
    dragging = False
    last_mouse = (0, 0)
    color_refresh = 0
    hist = []     # (a, fraction d'amas) pour la courbe

    while True:
        for ev in pygame.event.get():
            if ev.type == QUIT:
                return "quit"
            if ev.type == KEYDOWN:
                if ev.key == K_ESCAPE:
                    return "menu"
                if ev.key == K_SPACE:
                    paused = not paused
                elif ev.key in (K_PLUS, K_EQUALS, K_KP_PLUS):
                    steps_per_frame = min(steps_per_frame + 1, 40)
                elif ev.key in (K_MINUS, K_KP_MINUS):
                    steps_per_frame = max(steps_per_frame - 1, 1)
                elif ev.key == K_r:
                    sim = UniverseSim(params)
                    hist = []
                elif ev.key == K_c:
                    color_mode = (color_mode + 1) % len(COLOR_MODES)
                    colors = build_colors(sim, color_mode)
                elif ev.key == K_h:
                    species_view = (species_view + 1) % 3
                elif ev.key == K_b:
                    show_box = not show_box
                elif ev.key == K_p:
                    point_size = 1.0 if point_size > 3.0 else point_size + 0.8
            if ev.type == MOUSEBUTTONDOWN and ev.button == 1:
                dragging = True
                last_mouse = pygame.mouse.get_pos()
            if ev.type == MOUSEBUTTONUP and ev.button == 1:
                dragging = False
            if ev.type == MOUSEMOTION and dragging:
                mx, my = pygame.mouse.get_pos()
                cam.yaw += (mx - last_mouse[0]) * 0.35
                cam.pitch += (my - last_mouse[1]) * 0.35
                cam.pitch = max(-89.0, min(89.0, cam.pitch))
                last_mouse = (mx, my)
            if ev.type == MOUSEWHEEL:
                cam.zoom(ev.y)

        # ---- physique ----
        if not paused:
            for _ in range(steps_per_frame):
                sim.step(dt)
                # a = 1 correspond a l'epoque actuelle : on s'arrete la.
                if params.expansion and sim.a >= 1.0:
                    paused = True
                    break
            color_refresh += 1
            if color_refresh % 2 == 0:
                colors = build_colors(sim, color_mode)
            if sim.step_count % 5 == 0:
                hist.append((sim.a, sim.clump_fraction()))
                if len(hist) > 400:
                    hist.pop(0)

        # ---- rendu 3D ----
        glClearColor(*C_BG, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, WIDTH / float(HEIGHT), 0.01, 50.0)
        glMatrixMode(GL_MODELVIEW)
        cam.apply()

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)       # additif : les amas brillent
        glEnable(GL_POINT_SMOOTH)
        glPointSize(point_size)

        # Filtrage par espece : on envoie des copies contigues du
        # sous-ensemble, car les pointeurs OpenGL exigent un buffer compact.
        if species_view == 0 or not sim.p.janus:
            draw_pos, draw_col = sim.pos, colors
        else:
            sel = sim.idx_pos if species_view == 1 else sim.idx_neg
            draw_pos = np.ascontiguousarray(sim.pos[sel])
            draw_col = np.ascontiguousarray(colors[sel])

        if len(draw_pos):
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_COLOR_ARRAY)
            glVertexPointer(3, GL_DOUBLE, 0, draw_pos)
            glColorPointer(4, GL_FLOAT, 0, draw_col)
            glDrawArrays(GL_POINTS, 0, len(draw_pos))
            glDisableClientState(GL_COLOR_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)

        if show_box:
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            draw_box_wireframe()

        # ---- HUD 2D ----
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, WIDTH, 0, HEIGHT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # panneau gauche
        pw = 330
        ph = 222 if sim.p.janus else 180
        draw_gradient(16, HEIGHT - ph - 16, pw, ph, (28, 26, 46), (14, 13, 26))
        draw_border(16, HEIGHT - ph - 16, pw, ph)

        ty = HEIGHT - 44
        draw_text(f_btn, "UNIVERS PRIMORDIAL", C_TITLE, 32, ty)
        ty -= 30
        z = sim.redshift
        draw_text(f_small, "Facteur d'echelle  a = %.3f" % sim.a, C_TEXT, 32, ty)
        ty -= 20
        if params.expansion:
            draw_text(f_small, "Redshift           z = %.2f" % z, C_TEXT, 32, ty)
        else:
            draw_text(f_small, "Expansion desactivee", C_DIM, 32, ty)
        ty -= 20
        draw_text(f_small, "Temps ecoule  %.2f Gyr" % sim.age_gyr, C_TEXT, 32, ty)
        ty -= 20
        draw_text(f_small, "Matiere en amas  %.1f %%"
                  % (100.0 * sim.clump_fraction()), C_ACCENT, 32, ty)
        ty -= 20
        draw_text(f_small, "Particules %s   FPS %.0f"
                  % (f"{len(sim.pos):,}".replace(",", " "), clock.get_fps()),
                  C_DIM, 32, ty)
        ty -= 20
        draw_text(f_small, "Couleur : %s" % COLOR_MODES[color_mode], C_DIM, 32, ty)
        if sim.p.janus:
            ty -= 20
            vue = ("les deux especes", "matiere positive seule",
                   "masse negative seule")[species_view]
            draw_text(f_small, "JANUS  %d%% negatif  —  %s"
                      % (round(100.0 * len(sim.idx_neg) / max(len(sim.pos), 1)),
                         vue), (150, 210, 255), 32, ty)
            ty -= 20
            dp = sim.density_pos[sim.idx_pos]
            dn = sim.density_neg[sim.idx_neg]
            if len(dp) and len(dn):
                draw_text(f_small, "densite max  (+) %.0f   (-) %.0f"
                          % (dp.max(), dn.max()), C_DIM, 32, ty)

        # courbe de croissance des structures
        if len(hist) > 2:
            gx, gy, gw, gh = 16, HEIGHT - ph - 130, 330, 100
            draw_gradient(gx, gy, gw, gh, (26, 24, 42), (14, 13, 26))
            draw_border(gx, gy, gw, gh)
            draw_text(f_small, "Croissance des structures", C_DIM, gx + 10,
                      gy + gh - 20)
            vmax = max(max(h[1] for h in hist), 1e-3)
            glColor3f(1.0, 0.75, 0.35)
            glBegin(GL_LINE_STRIP)
            for i, (_, frac) in enumerate(hist):
                glVertex2f(gx + 10 + (gw - 20) * i / float(len(hist) - 1),
                           gy + 10 + (gh - 40) * frac / vmax)
            glEnd()

        # aide en bas
        gyr_per_s = (dt * steps_per_frame * 60.0 * MPC_PER_KM_S
                     / max(params.h0, 1e-6))
        help_txt = ("ESPACE pause   +/- vitesse (x%d ~ %.1f Gyr/s)   C couleur   "
                    "%sR relancer   B boite   P points   "
                    "souris orbiter / molette zoom   ECHAP menu"
                    % (steps_per_frame, gyr_per_s,
                       "H especes   " if sim.p.janus else ""))
        draw_rect(0, 0, WIDTH, 30, (10, 9, 18), 0.85)
        draw_text(f_small, help_txt, C_DIM, 20, 9)

        if paused:
            msg = ("EPOQUE ACTUELLE ATTEINTE (a = 1, z = 0) — R pour relancer"
                   if params.expansion and sim.a >= 1.0 else "PAUSE")
            surf = f_btn.render(msg, True, C_ACCENT)
            draw_text(f_btn, msg, C_ACCENT,
                      WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2)

        pygame.display.flip()
        clock.tick(60)


# ===========================================================================
#  POINT D'ENTREE
# ===========================================================================

def main():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Simulation de l'univers primordial")
    clock = pygame.time.Clock()

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    fonts = (
        pygame.font.SysFont("comicsans", 26),
        pygame.font.SysFont("comicsans", 15),
        pygame.font.SysFont("comicsans", 18),
        pygame.font.SysFont("comicsans", 14),
    )

    params = SimParams()

    while True:
        if not menu_screen(params, fonts, clock):
            break
        if simulate_screen(params, fonts, clock) == "quit":
            break

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
