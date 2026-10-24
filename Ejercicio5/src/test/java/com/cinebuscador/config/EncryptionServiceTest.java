package com.cinebuscador.config;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests de seguridad del Ejercicio 5.
 * Pruebo que las contrasenas se guarden de forma segura.
 * Correr con: cd Ejercicio5 && mvn test
 */
class EncryptionServiceTest {

    // Pruebo que la misma contrasena no genere siempre el mismo resultado.
    @Test
    void encriptarLaMismaContrasenaDosVecesNoDaElMismoResultado() {
        // En main, el resultado es siempre el mismo porque usa AES/ECB.
        // En Practico-2, BCrypt genera un resultado distinto cada vez.
        String resultado1 = EncryptionService.encrypt("12345678");
        String resultado2 = EncryptionService.encrypt("12345678");

        assertNotEquals(resultado1, resultado2,
            "el metodo encrypt() no deberia devolver siempre el mismo resultado");
    }

    // Pruebo que el resultado tenga el formato de un hash BCrypt.
    @Test
    void elResultadoDeEncriptarTieneElFormatoDeUnHashBcrypt() {
        // En main, la contrasena se cifra y el resultado se guarda en Base64.
        // Esto se puede revertir para recuperar la contrasena original.
        // En Practico-2, BCrypt genera un hash que no permite recuperar la
        // contrasena original directamente, por lo que es mas seguro para guardarlas.
        String resultado = EncryptionService.encrypt("Otra_contrasena_que_deberia_poder_descriptarse");

        assertTrue(resultado.matches("^\\$2[aby]?\\$\\d{2}\\$.{53}$"),
            "El resultado deberia tener el formato de un hash BCrypt");
    }

    // Pruebo que el metodo siga funcionando con una contrasena valida.
    @Test
    void encriptarUnaContrasenaValidaDevuelveUnResultadoNoVacio() {
        String resultado = EncryptionService.encrypt("Contrasena_Muy_Valida");

        // Compruebo que el resultado exista y no este vacio.
        assertNotNull(resultado);
        assertFalse(resultado.isBlank());
    }

    // Pruebo que la contrasena nunca quede guardada en texto plano.
    @Test
    void laContrasenaNuncaQuedaGuardadaEnTextoPlano() {
        // Esto deberia dar bien en las dos ramas: ni AES (main) ni BCrypt
        // (Practico-2) devuelven la contrasena original tal cual.
        String contrasena = "ContrasenaDePrueba123";
        String resultado = EncryptionService.encrypt(contrasena);

        assertNotEquals(contrasena, resultado,
            "encrypt() no deberia devolver la contrasena tal cual");
        assertFalse(resultado.contains(contrasena),
            "El resultado no deberia contener la contrasena en texto plano");
    }
}