# Shaders tiers embarqués

## Anime4K (embarqué)

Les fichiers `Anime4K_*.glsl` de ce dossier proviennent du projet **Anime4K**
(https://github.com/bloc97/Anime4K), utilisé ici comme moteur de super-résolution
neuronale temps réel exécuté par le pipeline GPU de libmpv.

Licence : **MIT** — Copyright (c) 2019 bloc97.

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## FSRCNNX (NON embarqué — téléchargé à la demande)

Le moteur **FSRCNNX** (https://github.com/igv/FSRCNN-TensorFlow), plus adapté à
la vidéosurveillance, est sous licence **GPL v3** : il n'est PAS redistribué avec
cette application. L'utilisateur peut le télécharger localement (bouton « Moteur
CCTV »), auquel cas le fichier reste sur son poste, dans le dossier `shaders` du
profil utilisateur. Aucun fichier GPL n'est présent dans ce dépôt.
