import pytest
from io import StringIO
from django.core.management import call_command
from accounts.models import Usuario
from plataformas.models import Plataforma
from chamados.models import Chamado


@pytest.mark.django_db
def test_popular_demo_command():
    out = StringIO()
    call_command("popular_demo", "--limpar", stdout=out)
    output = out.getvalue()

    assert "[OK] Usuarios criados" in output
    assert "[OK] 3 Plataformas" in output
    assert "[OK] 60 chamados criados" in output

    assert Usuario.objects.filter(username="gestor").exists()
    assert Usuario.objects.filter(username="dev_lucas").exists()
    assert Plataforma.objects.count() == 3
    assert Chamado.objects.count() == 60


@pytest.mark.django_db
def test_criar_admin_command():
    out = StringIO()
    call_command(
        "criar_admin",
        "--username", "novoadmin",
        "--email", "novoadmin@empresa.com",
        "--password", "senha123",
        stdout=out
    )
    assert Usuario.objects.filter(username="novoadmin", papel=Usuario.PAPEL_ADMIN).exists()
