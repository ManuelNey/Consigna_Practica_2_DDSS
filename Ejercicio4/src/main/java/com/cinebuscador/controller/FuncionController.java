package com.cinebuscador.controller;

import com.cinebuscador.model.Funcion;
import com.cinebuscador.repository.FuncionRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.ArrayList;
import java.util.List;

@Controller
public class FuncionController {

    private final FuncionRepository funcionRepo;

    @Autowired
    public FuncionController(FuncionRepository funcionRepo) {
        this.funcionRepo = funcionRepo;
    }

    @GetMapping("/")
    public String search(@RequestParam(required = false) String buscar, Model model) {

        model.addAttribute("query", buscar != null ? buscar : "");

        if (buscar == null || buscar.isBlank()) {
            List<Funcion> todas = funcionRepo.findAll();
            model.addAttribute("resultados", todas);
            model.addAttribute("mensaje", "Mostrando todas las funciones.");
            return "index";
        }

        List<Funcion> resultados = new ArrayList<>();
        for (Funcion f : funcionRepo.findAll()) {
            if (f.getNombreFuncion() != null && f.getNombreFuncion().toLowerCase().contains(buscar.toLowerCase())) {
                resultados.add(f);
            }
        }

        if (!resultados.isEmpty()) {
            model.addAttribute("resultados", resultados);
            model.addAttribute("mensaje", "Resultados buscando por: " + buscar);
        } else {
            model.addAttribute("mensaje", "No se encontraron coincidencias.");
        }

        return "index";
    }
}