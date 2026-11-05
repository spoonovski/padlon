// Společné připojení k Firebase pro stránky Zápasy a Žebříček.
// window.__MOCK_DB__ slouží k testování bez Firebase.
export const slug = s => s.trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"") || "hrac";

export async function connect(showError = console.error){
  if (window.__MOCK_DB__) return window.__MOCK_DB__;
  let cfg = null;
  try { cfg = (await import("./firebase-config.js?v=" + Date.now())).firebaseConfig; } catch(e){}
  if (!cfg || !cfg.apiKey) return null;
  const V = "10.12.2";
  const [{initializeApp}, fs, au] = await Promise.all([
    import(`https://www.gstatic.com/firebasejs/${V}/firebase-app.js`),
    import(`https://www.gstatic.com/firebasejs/${V}/firebase-firestore.js`),
    import(`https://www.gstatic.com/firebasejs/${V}/firebase-auth.js`),
  ]);
  const app = initializeApp(cfg);
  const auth = au.getAuth(app), db = fs.getFirestore(app);
  const email = name => `${slug(name)}@${cfg.authDomain}`;
  const watch = (col, from, cb) => fs.onSnapshot(
    fs.query(fs.collection(db, col), fs.where("date", ">=", from)),
    snap => cb(snap.docs.map(d => ({id: d.id, ...d.data()}))),
    err => showError("Nepodařilo se načíst data z Firebase: " + err.message));
  return {
    onAuth: cb => au.onAuthStateChanged(auth, u => cb(u && !u.isAnonymous ? {uid: u.uid} : null)),
    signUp: async (name, pass) => {
      const c = await au.createUserWithEmailAndPassword(auth, email(name), pass);
      await fs.setDoc(fs.doc(db, "players", c.user.uid), {name, created: Date.now()});
      return c.user.uid;
    },
    signIn: async (name, pass) => (await au.signInWithEmailAndPassword(auth, email(name), pass)).user.uid,
    signOut: () => au.signOut(auth),
    deleteAccount: async (name, pass, upcoming) => {
      const u = auth.currentUser;
      await au.reauthenticateWithCredential(u, au.EmailAuthProvider.credential(email(name), pass));
      const mine = await fs.getDocs(fs.query(fs.collection(db, "availability"), fs.where("player", "==", u.uid)));
      for (const d of mine.docs) await fs.deleteDoc(d.ref);
      for (const m of upcoming){
        const rest = m.players.filter(id => id !== u.uid);
        if (!rest.length) await fs.deleteDoc(fs.doc(db, "matches", m.id));
        else await fs.updateDoc(fs.doc(db, "matches", m.id), {players: rest, ...(m.booked === u.uid ? {booked: null} : {})});
      }
      await fs.deleteDoc(fs.doc(db, "players", u.uid));
      await au.deleteUser(u);
    },
    getPlayer: async uid => { const d = await fs.getDoc(fs.doc(db, "players", uid)); return d.exists() ? d.data() : null; },
    setPlayer: (uid, data) => fs.setDoc(fs.doc(db, "players", uid), data),
    updatePlayer: (uid, data) => fs.updateDoc(fs.doc(db, "players", uid), data),
    watchPlayers: cb => fs.onSnapshot(fs.collection(db, "players"), snap => cb(snap.docs.map(d => ({id: d.id, ...d.data()}))),
      err => showError("Nepodařilo se načíst hráče: " + err.message)),
    watchAvailability: (from, cb) => watch("availability", from, cb),
    watchMatches: (from, cb) => watch("matches", from, cb),
    setAvailability: (id, data) => fs.setDoc(fs.doc(db, "availability", id), data),
    addMatch: data => fs.addDoc(fs.collection(db, "matches"), data),
    updateMatch: (id, data) => fs.updateDoc(fs.doc(db, "matches", id), data),
    deleteMatch: id => fs.deleteDoc(fs.doc(db, "matches", id)),
  };
}
