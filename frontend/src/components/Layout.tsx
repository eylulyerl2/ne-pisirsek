import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { keepParams } from "../utils/nav";
import { Icon } from "./Icon";

export function Layout() {
  const { user, logout } = useAuth();
  const { search } = useLocation();
  const weekSearch = keepParams(search);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/plan" className="brand">
            <span className="brand-mark">
              <Icon name="pot" size={20} />
            </span>
            Ne Pişirsek?
          </NavLink>
          <div className="spacer" />
          <nav className="nav" aria-label="Ana menü">
            <NavLink to={{ pathname: "/plan", search: weekSearch }}>
              <Icon name="calendar" />
              Plan
            </NavLink>
            <NavLink to={{ pathname: "/alisveris", search: weekSearch }}>
              <Icon name="cart" />
              Alışveriş
            </NavLink>
            <NavLink to="/aile">
              <Icon name="users" />
              Aile
            </NavLink>
            <NavLink to="/yemekler">
              <Icon name="book" />
              Yemekler
            </NavLink>
            <NavLink to="/tercihler">
              <Icon name="sliders" />
              Tercihler
            </NavLink>
          </nav>
          <div className="user-menu">
            <span>{user?.full_name}</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={logout} aria-label="Çıkış yap">
              <Icon name="logout" size={18} />
              <span>Çıkış</span>
            </button>
          </div>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}
