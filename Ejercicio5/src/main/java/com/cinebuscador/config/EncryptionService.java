package com.cinebuscador.config;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

/**
 * Servicio de hasheo de contraseñas con BCrypt.
 *
 * A diferencia del cifrado (AES), el hash es irreversible: nunca se puede
 * recuperar la contraseña original a partir del hash guardado. Para
 * verificar un login, se compara el hash de lo ingresado contra el hash
 * almacenado, sin necesidad de descifrar nada.
 */
public class EncryptionService {

    private static final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    /**
     * Genera el hash de una contraseña en texto plano.
     */
    public static String encrypt(String plaintext) {
        return encoder.encode(plaintext);
    }

    /**
     * Compara una contraseña en texto plano contra un hash ya almacenado.
     * Devuelve true si coinciden, sin necesidad de revertir el hash.
     */
    public static boolean matches(String plaintext, String hash) {
        return encoder.matches(plaintext, hash);
    }
}